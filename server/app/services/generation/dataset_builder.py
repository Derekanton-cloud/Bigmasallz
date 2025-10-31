"""Utilities for assembling and persisting generated datasets."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class DatasetBuilder:
    """Merge chunks, apply hybrid data and persist to disk."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def merge_hybrid_values(
        self,
        rows: List[Dict[str, Any]],
        hybrid_values: Dict[str, List[Any]],
    ) -> List[Dict[str, Any]]:
        if not hybrid_values:
            return rows
        for column_name, values in hybrid_values.items():
            for idx, value in enumerate(values):
                if idx < len(rows):
                    rows[idx][column_name] = value
        return rows

    def write_outputs(
        self,
        task_id: str,
        rows: Iterable[Dict[str, Any]],
        formats: Iterable[str],
    ) -> Dict[str, str]:
        formats = list(formats)
        rows_list = list(rows)
        output_map: Dict[str, str] = {}
        for fmt in formats:
            fmt = fmt.lower()
            if fmt == "csv":
                output_map["csv"] = self._write_csv(task_id, rows_list)
            elif fmt == "json":
                output_map["json"] = self._write_json(task_id, rows_list)
        return output_map

    def _write_csv(self, task_id: str, rows: List[Dict[str, Any]]) -> str:
        if not rows:
            raise ValueError("No rows available for CSV export")
        headers = rows[0].keys()
        file_path = self._output_dir / f"{task_id}.csv"
        with file_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        return str(file_path)

    def _write_json(self, task_id: str, rows: List[Dict[str, Any]]) -> str:
        file_path = self._output_dir / f"{task_id}.json"
        with file_path.open("w", encoding="utf-8") as json_file:
            json.dump(rows, json_file, indent=2)
        return str(file_path)
