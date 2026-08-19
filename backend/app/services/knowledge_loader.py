import json
from pathlib import Path
from typing import Any

from app.schemas import KnowledgeEntryCreate


class KnowledgeLoaderError(Exception):
    pass


class KnowledgeLoader:
    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir)

    def _discover_files(self) -> list[Path]:
        if not self._root.exists():
            raise KnowledgeLoaderError(f"Knowledge base directory does not exist: {self._root}")
        if not self._root.is_dir():
            raise KnowledgeLoaderError(f"Knowledge base path is not a directory: {self._root}")

        files: list[Path] = []
        for pattern in ("**/*.json", "**/*.jsonl"):
            files.extend(self._root.glob(pattern))
        return sorted(files)

    def _read_objects(self, file_path: Path) -> list[dict[str, Any]]:
        text = file_path.read_text(encoding="utf-8")
        stripped = text.strip()
        if not stripped:
            return []

        # JSON Lines: one JSON object per line.
        if file_path.suffix.lower() == ".jsonl":
            objects: list[dict[str, Any]] = []
            for line_number, line in enumerate(stripped.splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise KnowledgeLoaderError(
                        f"Invalid JSON at {file_path}:{line_number}: {exc}"
                    ) from exc
                if not isinstance(obj, dict):
                    raise KnowledgeLoaderError(
                        f"Expected JSON object at {file_path}:{line_number}, got {type(obj).__name__}"
                    )
                objects.append(obj)
            return objects

        # Standard JSON array.
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise KnowledgeLoaderError(f"Invalid JSON in {file_path}: {exc}") from exc

        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    raise KnowledgeLoaderError(
                        f"Expected JSON object at {file_path}[{idx}], got {type(item).__name__}"
                    )
            return data
        raise KnowledgeLoaderError(
            f"Expected JSON object or array in {file_path}, got {type(data).__name__}"
        )

    def _validate_entry(self, raw: dict[str, Any], file_path: Path) -> KnowledgeEntryCreate:
        try:
            return KnowledgeEntryCreate(**raw)
        except Exception as exc:
            raise KnowledgeLoaderError(
                f"Invalid knowledge entry in {file_path}: {exc}"
            ) from exc

    def load(self) -> list[KnowledgeEntryCreate]:
        files = self._discover_files()
        entries: list[KnowledgeEntryCreate] = []
        for file_path in files:
            objects = self._read_objects(file_path)
            for obj in objects:
                entries.append(self._validate_entry(obj, file_path))
        return entries
