"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Bot, Cpu, Database } from "lucide-react";

import ChatConsole from "./components/ChatConsole";
import SynthesisTimeline from "./components/SynthesisTimeline";
import SchemaArchitect from "./components/SchemaArchitect";
import SignalTelemetry from "./components/SignalTelemetry";
import DatasetPreview from "./components/DatasetPreview";

import type {
  ChatMessage,
  FieldDefinition,
  DatasetStats,
  LlmMetric,
  TelemetrySignal,
} from "./components/types";

import {
  PROGRESS_STEPS,
  LLM_METRIC_TEMPLATES,
  DEFAULT_FIELDS,
} from "./components/constants";

type JobStatus =
  | "pending"
  | "schema_validation"
  | "generating"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

interface SchemaFieldPayload {
  name: string;
  type: string;
  description?: string;
  constraints?: Record<string, any>;
  sample_values?: string[];
}

interface SchemaExtractResponse {
  schema: {
    description?: string;
    fields: SchemaFieldPayload[];
  };
  confidence: number;
  suggestions: string[];
  warnings: string[];
}

interface JobProgressDetail {
  status: JobStatus;
  rows_generated: number;
  total_rows: number;
  chunks_completed: number;
  total_chunks: number;
  progress_percentage: number;
  current_chunk: number | null;
  started_at: string | null;
  completed_at: string | null;
  paused_at: string | null;
  estimated_completion: string | null;
  error_message: string | null;
}

interface JobCreateResponse {
  job_id: string;
  status: JobStatus;
  total_rows: number;
  chunk_size: number;
  total_chunks: number;
  output_format: string;
  storage_type: string;
  uniqueness_fields: string[];
  seed: number | null;
  job_progress: JobProgressDetail;
  message: string;
  auto_started: boolean;
}

interface JobProgressResponse {
  job_id: string;
  job_progress: JobProgressDetail;
}

interface JobDetailResponse {
  job_id: string;
  status: JobStatus;
  total_rows: number;
  chunk_size: number;
  output_format: string;
  storage_type: string;
  uniqueness_fields: string[];
  seed: number | null;
  created_at: string;
  metadata: Record<string, any>;
  schema: {
    description?: string;
    fields: SchemaFieldPayload[];
    metadata?: Record<string, any>;
  };
  schema_validated: boolean;
  can_resume: boolean;
  job_progress: JobProgressDetail;
  download_url: string | null;
}

interface JobMergeResponse {
  job_id: string;
  file_path: string | null;
  file_size_bytes: number | null;
  format: string;
  total_rows: number;
  checksum: string;
  download_url: string | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const slugify = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "")
    .slice(0, 40) || "synthetic_dataset";

const formatBytes = (bytes?: number | null) => {
  if (!bytes || bytes <= 0) return "0 MB";
  const megabytes = bytes / (1024 * 1024);
  if (megabytes < 1) {
    const kilobytes = bytes / 1024;
    return `${kilobytes.toFixed(1)} KB`;
  }
  return `${megabytes.toFixed(2)} MB`;
};

const formatDuration = (start?: string | null, end?: string | null) => {
  if (!start || !end) return "--";
  const startDate = new Date(start);
  const endDate = new Date(end);
  const diffMs = endDate.getTime() - startDate.getTime();
  if (Number.isNaN(diffMs) || diffMs <= 0) return "--";
  const seconds = diffMs / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = seconds / 60;
  return `${minutes.toFixed(1)}m`;
};

const parseCsvPreview = (csvText: string, limit = 5) => {
  const lines = csvText.trim().split(/\r?\n/);
  if (lines.length <= 1) return [];
  const headers = lines[0].split(",").map((header) => header.trim());
  return lines
    .slice(1, limit + 1)
    .map((line) => {
      const cells = line.split(",");
      const row: Record<string, any> = {};
      headers.forEach((header, index) => {
        row[header] = cells[index]?.trim() ?? "";
      });
      return row;
    })
    .filter((row) => Object.keys(row).length > 0);
};

const parseJsonPreview = (jsonText: string, limit = 5) => {
  const trimmed = jsonText.trim();
  if (!trimmed) return [];

  const coerceRecord = (value: unknown) => {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return value as Record<string, any>;
    }
    return { value } as Record<string, any>;
  };

  try {
    const parsed = JSON.parse(trimmed);
    if (Array.isArray(parsed)) {
      return parsed.slice(0, limit).map((item) => coerceRecord(item));
    }
    if (parsed && typeof parsed === "object") {
      return Object.entries(parsed)
        .slice(0, limit)
        .map(([key, value]) => ({ key, value }));
    }
  } catch (error) {
    const lines = trimmed.split(/\r?\n/).filter(Boolean);
    const parsedLines = lines
      .slice(0, limit)
      .map((line) => {
        try {
          return coerceRecord(JSON.parse(line));
        } catch {
          return null;
        }
      })
      .filter((record): record is Record<string, any> => record !== null);
    if (parsedLines.length > 0) {
      return parsedLines;
    }
  }

  return [];
};

const convertSchemaToFields = (schemaFields: SchemaFieldPayload[]): FieldDefinition[] =>
  schemaFields.map((field, index) => ({
    id: index + 1,
    name: field.name,
    type: field.type,
    description: field.description ?? "",
    synthetic: true,
    example: field.sample_values?.[0] ?? "",
    constraints: field.constraints,
    sampleValues: field.sample_values ?? [],
  }));

const buildSchemaPayload = (fields: FieldDefinition[], description: string) => ({
  description: description || undefined,
  fields: fields.map((field) => ({
    name: field.name,
    type: field.type,
    description: field.description || undefined,
    constraints: field.constraints ?? {},
    sample_values:
      field.sampleValues && field.sampleValues.length > 0
        ? field.sampleValues
        : field.example
        ? [field.example]
        : [],
  })),
});

const mapStatusToStep = (status: JobStatus): number => {
  switch (status) {
    case "pending":
      return 0;
    case "schema_validation":
      return 1;
    case "generating":
    case "paused":
      return 2;
    case "completed":
    case "failed":
    case "cancelled":
    default:
      return PROGRESS_STEPS.length - 1;
  }
};

const buildTelemetrySignals = (progress: JobProgressDetail | null): TelemetrySignal[] => {
  const percentage = progress?.progress_percentage ?? 0;
  const rowsGenerated = progress?.rows_generated ?? 0;
  return [
    {
      id: "progress",
      label: "Progress",
      caption: `${rowsGenerated.toLocaleString()} rows generated`,
      accent: "emerald",
      type: "gauge",
      percentage,
      status: progress?.status === "failed" ? "warning" : "active",
      icon: Cpu,
    },
    {
      id: "chunks",
      label: "Chunks",
      caption: `${progress?.chunks_completed ?? 0}/${progress?.total_chunks ?? 0} complete`,
      accent: "cyan",
      type: "gauge",
      percentage: progress?.total_chunks
        ? Math.min(100, ((progress.chunks_completed / progress.total_chunks) * 100))
        : 0,
      status: "active",
      icon: Database,
    },
    {
      id: "eta",
      label: "ETA",
      caption: progress?.estimated_completion
        ? new Date(progress.estimated_completion).toLocaleTimeString()
        : "Calculating",
      accent: "amber",
      type: "spark",
      points: Array.from({ length: 20 }, (_, index) =>
        Math.max(0, percentage - index * (percentage / 20))
      ),
    },
  ];
};

export default function SynthxAI() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: "system",
      content:
        "SynthxAI dataset synthesis engine online. Describe the dataset you need and I will craft the schema, generate synthetic rows, and deliver a CSV export.",
      timestamp: new Date().toLocaleTimeString(),
    },
    {
      id: 2,
      role: "agent",
      content:
        "Start by describing your dataset goals in the chat or the narrative panel. I can auto-design the schema before we launch generation.",
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");

  const [datasetName, setDatasetName] = useState("customer_analytics");
  const [datasetNarrative, setDatasetNarrative] = useState(
    "Enterprise customer behavior and engagement metrics for B2B SaaS platforms",
  );
  const [rowCount, setRowCount] = useState(10000);
  const [chunkSize, setChunkSize] = useState(1000);
  const [outputFormat, setOutputFormat] = useState("csv");
  const [fields, setFields] = useState<FieldDefinition[]>(DEFAULT_FIELDS);
  const [nextFieldId, setNextFieldId] = useState(DEFAULT_FIELDS.length + 1);
  const [schemaConfidence, setSchemaConfidence] = useState<number | null>(null);
  const [isExtractingSchema, setIsExtractingSchema] = useState(false);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isGenerated, setIsGenerated] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [jobProgress, setJobProgress] = useState<JobProgressDetail | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [previewData, setPreviewData] = useState<Array<Record<string, any>>>([]);
  const [stats, setStats] = useState<DatasetStats>({
    rows: 0,
    columns: 0,
    estimatedSize: "0 MB",
    syntheticScore: 0,
    generationTime: "--",
  });

  const telemetryData = useMemo(() => buildTelemetrySignals(jobProgress), [jobProgress]);
  const [llmMetrics, setLlmMetrics] = useState<LlmMetric[]>(LLM_METRIC_TEMPLATES);

  useEffect(() => {
    if (!isGenerating) return;
    const interval = setInterval(() => {
      setLlmMetrics((prev) =>
        prev.map((metric) => ({
          ...metric,
          value: generateMetricValue(metric.label),
          trend: Math.random() > 0.5 ? "up" : "down",
        })),
      );
    }, 2500);
    return () => clearInterval(interval);
  }, [isGenerating]);

  const generateMetricValue = (label: string): string => {
    switch (label) {
      case "Tokens / sec":
        return `${(Math.random() * 25 + 40).toFixed(1)}k`;
      case "Latency":
        return `${Math.floor(Math.random() * 70 + 90)} ms`;
      case "Context load":
        return `${Math.floor(Math.random() * 25 + 65)} %`;
      case "Coherence":
        return `${Math.floor(Math.random() * 6 + 93)} %`;
      default:
        return "0";
    }
  };

  const appendMessage = useCallback((message: Omit<ChatMessage, "id" | "timestamp">) => {
    setMessages((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        role: message.role,
        content: message.content,
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
  }, []);

  const handleExtractSchema = useCallback(
    async (prompt?: string) => {
      const narrative = (prompt ?? datasetNarrative).trim();
      if (!narrative) {
        setErrorMessage("Please describe the dataset before asking for a schema suggestion.");
        return;
      }

      setErrorMessage(null);
      setIsExtractingSchema(true);
      try {
        const response = await fetch(`${API_BASE_URL}/schema/extract`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_input: narrative }),
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail ?? "Schema extraction failed");
        }

        const data: SchemaExtractResponse = await response.json();
        const mappedFields = convertSchemaToFields(data.schema.fields);
        setFields(mappedFields);
        setNextFieldId(mappedFields.length + 1);
        setSchemaConfidence(data.confidence);
        setDatasetNarrative(narrative);

        if (!datasetName.trim() || datasetName === "customer_analytics") {
          setDatasetName(slugify(narrative));
        }

        appendMessage({
          role: "agent",
          content: `Schema drafted with ${mappedFields.length} fields (confidence ${(data.confidence * 100).toFixed(1)}%). Review or tweak the blueprint before generating rows.`,
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Schema extraction failed";
        setErrorMessage(message);
        appendMessage({
          role: "agent",
          content: `I couldn't extract a schema: ${message}. Please refine the description and try again.`,
        });
      } finally {
        setIsExtractingSchema(false);
      }
    },
    [appendMessage, datasetName, datasetNarrative],
  );

  const handleSendMessage = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!inputValue.trim()) return;

      const content = inputValue.trim();
      setInputValue("");
      appendMessage({ role: "user", content });
      handleExtractSchema(content);
    },
    [appendMessage, handleExtractSchema, inputValue],
  );

  const handleAddField = useCallback(() => {
    setFields((prev) => [
      ...prev,
      {
        id: nextFieldId,
        name: "",
        type: "string",
        description: "",
        synthetic: false,
        example: "",
        constraints: { nullable: true },
        sampleValues: [],
      },
    ]);
    setNextFieldId((prev) => prev + 1);
  }, [nextFieldId]);

  const handleFieldChange = useCallback(
    (
      fieldId: number,
      key: keyof FieldDefinition,
      value: FieldDefinition[keyof FieldDefinition],
    ) => {
      setFields((prev) =>
        prev.map((field) => {
          if (field.id !== fieldId) return field;
          if (key === "example") {
            const exampleValue = value as string;
            return {
              ...field,
              example: exampleValue,
              sampleValues: exampleValue ? [exampleValue] : [],
            };
          }
          if (key === "constraints") {
            return {
              ...field,
              constraints: (value as FieldDefinition["constraints"]) ?? undefined,
            };
          }
          return { ...field, [key]: value };
        }),
      );
    },
    [],
  );

  const handleRemoveField = useCallback((fieldId: number) => {
    setFields((prev) => prev.filter((field) => field.id !== fieldId));
  }, []);

  const runJobGeneration = useCallback(async (job: JobCreateResponse) => {
    const jobIdValue = job.job_id;
    const pollJob = async (): Promise<JobDetailResponse> => {
      while (true) {
        const progressResponse = await fetch(`${API_BASE_URL}/jobs/${jobIdValue}/progress`);
        if (!progressResponse.ok) {
          const detail = await progressResponse.json().catch(() => ({}));
          throw new Error(detail.detail ?? "Failed to read job progress");
        }
        const progressData: JobProgressResponse = await progressResponse.json();
        setJobProgress(progressData.job_progress);
        setJobStatus(progressData.job_progress.status);
        setCurrentStep(mapStatusToStep(progressData.job_progress.status));

        if (progressData.job_progress.status === "failed") {
          throw new Error(progressData.job_progress.error_message ?? "Job failed");
        }

        if (progressData.job_progress.status === "completed") {
          const detailResponse = await fetch(`${API_BASE_URL}/jobs/${jobIdValue}`);
          if (!detailResponse.ok) {
            const detail = await detailResponse.json().catch(() => ({}));
            throw new Error(detail.detail ?? "Failed to fetch job detail");
          }
          const detailData: JobDetailResponse = await detailResponse.json();
          setJobProgress(detailData.job_progress);
          setJobStatus(detailData.status);
          setCurrentStep(mapStatusToStep(detailData.status));
          return detailData;
        }

        await delay(2000);
      }
    };

    if (!job.auto_started) {
      const runResponse = await fetch(`${API_BASE_URL}/jobs/${jobIdValue}/run`, {
        method: "POST",
      });
      if (!runResponse.ok) {
        const detail = await runResponse.json().catch(() => ({}));
        throw new Error(detail.detail ?? "Failed to start job execution");
      }
    }

    return pollJob();
  }, []);

  const handleGenerateDataset = useCallback(async () => {
    if (!fields.length) {
      setErrorMessage("Define at least one field before generating the dataset.");
      return;
    }

    if (fields.some((field) => !field.name.trim())) {
      setErrorMessage("All fields must have a name. Please review the schema.");
      return;
    }

    const schemaPayload = buildSchemaPayload(fields, datasetNarrative);
    const uniquenessCandidates = Array.from(
      new Set(
        fields
          .filter(
            (field) =>
              field.constraints?.unique || field.name.toLowerCase().includes("id"),
          )
          .map((field) => field.name),
      ),
    );

    const payload = {
      schema: schemaPayload,
      total_rows: Math.max(100, rowCount),
      chunk_size: Math.max(100, Math.min(chunkSize, rowCount)),
      output_format: outputFormat,
      name: datasetName,
      description: datasetNarrative,
      metadata: {
        source: "synthx-ui",
        requested_rows: rowCount,
      },
      uniqueness_fields: uniquenessCandidates,
      auto_start: true,
    };

    setIsGenerating(true);
    setIsGenerated(false);
    setPreviewData([]);
    setStats({ rows: 0, columns: 0, estimatedSize: "0 MB", syntheticScore: 0, generationTime: "--" });
    setDownloadUrl(null);
    setErrorMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail ?? "Job creation failed");
      }
      const job: JobCreateResponse = await response.json();
      setJobId(job.job_id);
      setJobProgress(job.job_progress);
      setJobStatus(job.status);
      setCurrentStep(mapStatusToStep(job.status));

      appendMessage({
        role: "agent",
        content: `Job ${job.job_id} created. Generating ${job.total_rows.toLocaleString()} rows in ${job.total_chunks} chunk(s). I'll report progress as it completes.`,
      });

      const detail = await runJobGeneration(job);

      if (detail?.schema?.fields) {
        const finalFields = convertSchemaToFields(
          detail.schema.fields as SchemaFieldPayload[],
        );
        setFields(finalFields);
        setNextFieldId(finalFields.length + 1);
      }

      const mergeResponse = await fetch(`${API_BASE_URL}/jobs/${job.job_id}/merge`, {
        method: "POST",
      });
      if (!mergeResponse.ok) {
        const detailBody = await mergeResponse.json().catch(() => ({}));
        throw new Error(detailBody.detail ?? "Failed to merge dataset");
      }
      const merge: JobMergeResponse = await mergeResponse.json();
      const relativeDownload = merge.download_url ?? detail.download_url ?? `/jobs/${job.job_id}/download`;
      const absoluteDownloadUrl = new URL(relativeDownload, API_BASE_URL).href;

      const columnCount = Array.isArray(detail?.schema?.fields)
        ? detail.schema.fields.length
        : schemaPayload.fields.length;

      setDownloadUrl(absoluteDownloadUrl);
      setJobStatus(detail.status);
      setJobProgress(detail.job_progress);
      setStats({
        rows: merge.total_rows,
        columns: columnCount,
        estimatedSize: formatBytes(merge.file_size_bytes),
        syntheticScore: 100,
        generationTime: formatDuration(detail.job_progress.started_at, detail.job_progress.completed_at),
        fileSizeBytes: merge.file_size_bytes ?? undefined,
      });

      try {
        if (merge.format === "csv") {
          const csvContent = await fetch(absoluteDownloadUrl).then((res) => res.text());
          setPreviewData(parseCsvPreview(csvContent, 5));
        } else if (merge.format === "json") {
          const jsonContent = await fetch(absoluteDownloadUrl).then((res) => res.text());
          setPreviewData(parseJsonPreview(jsonContent, 5));
        } else {
          setPreviewData([]);
        }
      } catch (previewError) {
        console.warn("Failed to load dataset preview", previewError);
        setPreviewData([]);
      }

      setIsGenerated(true);
      setCurrentStep(PROGRESS_STEPS.length - 1);
      appendMessage({
        role: "agent",
        content: `All done! Dataset ready with ${merge.total_rows.toLocaleString()} rows. Use the download button above to export the ${merge.format.toUpperCase()} file.`,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Generation failed";
      setErrorMessage(message);
      appendMessage({
        role: "agent",
        content: `The generation pipeline encountered an issue: ${message}. Please adjust the schema or try again.`,
      });
    } finally {
      setIsGenerating(false);
    }
  }, [appendMessage, chunkSize, datasetNarrative, datasetName, fields, outputFormat, rowCount, runJobGeneration]);

  return (
    <main className="min-h-screen bg-linear-to-br from-slate-950 via-slate-900 to-black text-slate-100">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,var(--tw-gradient-stops))] from-cyan-500/12 via-blue-500/8 to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,var(--tw-gradient-stops))] from-violet-500/12 via-purple-500/8 to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,var(--tw-gradient-stops))] from-emerald-500/6 via-transparent to-transparent" />
        <div className="absolute inset-0 bg-grid-white/[0.04] bg-size-[80px_80px] animate-pulse" style={{ animationDuration: "6s" }} />
        <div className="absolute top-1/5 left-1/6 w-[500px] h-[500px] bg-cyan-500/8 rounded-full blur-3xl animate-bounce opacity-60" style={{ animationDuration: "8s" }} />
        <div className="absolute bottom-1/5 right-1/6 w-[400px] h-[400px] bg-violet-500/8 rounded-full blur-3xl animate-bounce opacity-60" style={{ animationDuration: "10s", animationDelay: "3s" }} />
        <div className="absolute inset-0 bg-linear-to-b from-transparent via-cyan-500/8 to-transparent h-1 animate-pulse" style={{ top: "25%" }} />
        <div className="absolute inset-0 bg-linear-to-b from-transparent via-violet-500/8 to-transparent h-1 animate-pulse" style={{ top: "65%", animationDelay: "2s" }} />
      </div>

      <header className="relative border-b border-slate-800/60 bg-slate-900/40 backdrop-blur-xl">
        <div className="absolute inset-0 bg-linear-to-r from-cyan-500/5 via-transparent to-violet-500/5" />
        <div className="mx-auto max-w-7xl px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative group">
                <div className="rounded-2xl border border-cyan-400/40 bg-linear-to-br from-cyan-500/20 to-blue-600/20 p-3 shadow-lg">
                  <Bot className="h-7 w-7 text-cyan-300" />
                </div>
                <div className="absolute -inset-2 rounded-2xl bg-linear-to-r from-cyan-400/20 to-blue-500/20 blur-lg opacity-50 group-hover:opacity-75 transition-opacity duration-300" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-linear-to-r from-cyan-200 via-blue-200 to-violet-200 bg-clip-text text-transparent">
                  SynthxAI
                </h1>
                <p className="text-sm text-slate-400 font-medium">Natural language to synthetic datasets, ready for download.</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 rounded-full border border-emerald-400/50 bg-linear-to-r from-emerald-500/20 to-green-500/20 px-4 py-2 shadow-lg">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]" />
                  <span className="text-sm font-semibold text-emerald-300">ONLINE</span>
                </div>
                <div className="flex items-center gap-2 rounded-full border border-blue-400/50 bg-linear-to-r from-blue-500/20 to-cyan-500/20 px-4 py-2 shadow-lg">
                  <div className="h-2 w-2 rounded-full bg-blue-400 animate-ping" />
                  <span className="text-sm font-semibold text-blue-300">
                    {jobStatus ? jobStatus.toUpperCase() : "IDLE"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="relative mx-auto max-w-[1600px] 3xl:max-w-[1800px] 4xl:max-w-[2000px] px-6 lg:px-8 py-12 space-y-6">
        {errorMessage && (
          <div className="rounded-2xl border border-amber-400/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200 shadow-[0_0_35px_rgba(251,191,36,0.25)]">
            {errorMessage}
          </div>
        )}

        <div className="grid gap-8 lg:gap-12 grid-cols-1 lg:grid-cols-[1.2fr_580px] xl:grid-cols-[1.3fr_650px] 2xl:grid-cols-[1.4fr_720px] 3xl:grid-cols-[1.5fr_800px] 4xl:grid-cols-[1.6fr_850px]">
          <div className="space-y-12">
            <div className="group relative">
              <div className="absolute -inset-4 bg-linear-to-br from-cyan-500/15 via-blue-500/10 to-violet-500/15 rounded-4xl blur-2xl opacity-0 group-hover:opacity-100 transition-all duration-700" />
              <div className="relative">
                <SchemaArchitect
                  datasetName={datasetName}
                  setDatasetName={setDatasetName}
                  datasetNarrative={datasetNarrative}
                  setDatasetNarrative={setDatasetNarrative}
                  rowCount={rowCount}
                  setRowCount={setRowCount}
                  chunkSize={chunkSize}
                  setChunkSize={setChunkSize}
                  outputFormat={outputFormat}
                  setOutputFormat={setOutputFormat}
                  fields={fields}
                  onAddField={handleAddField}
                  onFieldChange={handleFieldChange}
                  onRemoveField={handleRemoveField}
                  onGenerateDataset={handleGenerateDataset}
                  isGenerating={isGenerating}
                  onExtractSchema={() => handleExtractSchema()}
                  isExtractingSchema={isExtractingSchema}
                  schemaConfidence={schemaConfidence}
                />
              </div>
            </div>

            <div className="grid gap-6 md:gap-8 grid-cols-1 md:grid-cols-2 min-h-0">
              <div className="group relative w-full">
                <div className="absolute -inset-4 bg-linear-to-br from-emerald-500/15 via-green-500/10 to-cyan-500/15 rounded-4xl blur-2xl opacity-0 group-hover:opacity-100 transition-all duration-700" />
                <div className="relative w-full">
                  <SynthesisTimeline
                    isGenerating={isGenerating}
                    activeStepIndex={currentStep}
                    llmMetrics={llmMetrics}
                  />
                </div>
              </div>

              <div className="group relative w-full">
                <div className="absolute -inset-4 bg-linear-to-br from-amber-500/15 via-orange-500/10 to-red-500/15 rounded-4xl blur-2xl opacity-0 group-hover:opacity-100 transition-all duration-700" />
                <div className="relative w-full">
                  <SignalTelemetry telemetryData={telemetryData} />
                </div>
              </div>
            </div>

            <div className="group relative">
              <div className="absolute -inset-4 bg-linear-to-br from-violet-500/15 via-purple-500/10 to-pink-500/15 rounded-4xl blur-2xl opacity-0 group-hover:opacity-100 transition-all duration-700" />
              <div className="relative">
                <DatasetPreview
                  isGenerated={isGenerated}
                  previewData={previewData}
                  fields={fields}
                  stats={stats}
                  downloadUrl={downloadUrl}
                />
              </div>
            </div>
          </div>

          <div className="sticky top-8 h-fit">
            <div className="space-y-8">
              <div className="group relative">
                <div className="absolute -inset-6 bg-linear-to-br from-blue-500/20 via-indigo-500/15 to-cyan-500/20 rounded-4xl blur-2xl opacity-0 group-hover:opacity-100 transition-all duration-700" />
                <div className="relative">
                  <ChatConsole
                    messages={messages}
                    chatDraft={inputValue}
                    setChatDraft={setInputValue}
                    onSendMessage={handleSendMessage}
                  />
                </div>
              </div>

              {/* System Status - Better positioned */}
              <div className="group relative">
                <div className="absolute -inset-4 bg-linear-to-br from-emerald-500/15 via-teal-500/10 to-blue-500/15 rounded-4xl blur-2xl opacity-0 group-hover:opacity-100 transition-all duration-700" />
                <div className="relative rounded-3xl border border-emerald-500/30 bg-slate-900/85 p-6 shadow-2xl backdrop-blur-sm">
                  <h3 className="text-lg font-semibold bg-linear-to-r from-emerald-200 to-cyan-200 bg-clip-text text-transparent mb-4">
                    System Status
                  </h3>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">Active Sessions</span>
                      <span className="text-emerald-300 font-semibold">3,247</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">Data Generated</span>
                      <span className="text-cyan-300 font-semibold">847.2 MB</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">Uptime</span>
                      <span className="text-violet-300 font-semibold">99.8%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">AI Accuracy</span>
                      <span className="text-amber-300 font-semibold">97.3%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
