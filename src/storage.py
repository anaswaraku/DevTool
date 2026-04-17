"""
storage.py — StorageManager: persists ScrapeResults as JSON files
and maintains a registry of all scraped apps.

File layout:
  data/{app_id}.json        — full ScrapeResult payload
  data/registry.json        — list of AppRecord dicts (the index)
"""

import json
import os
import re
from dataclasses import asdict
from datetime import datetime

from src.config import DATA_DIR
from src.models import ScrapeResult, AppRecord

REGISTRY_PATH = os.path.join(DATA_DIR, "registry.json")


class StorageManager:

    # ── Public API ────────────────────────────────────────────────────

    def save(self, result: ScrapeResult, app_id: str) -> AppRecord:
        """
        Persist a ScrapeResult to disk and register the AppRecord.
        Returns the newly created AppRecord.
        """
        slug = self._slugify(result.app_name)
        filename = f"{app_id}.json"
        file_path = os.path.join(DATA_DIR, filename)

        # Write scrape data
        payload = asdict(result)
        payload["saved_at"] = datetime.now().isoformat()
        self._write_json(file_path, payload)

        # Create and register AppRecord
        record = AppRecord(
            id=app_id,
            app_name=result.app_name,
            url=result.url,
            tool_used=result.tool_used,
            file_path=file_path,
            endpoint_count=len(result.endpoints),
        )
        self._upsert_registry(record)
        return record

    def load(self, app_id: str) -> dict:
        """
        Load and return the raw data dict for a given app_id.
        First tries registry, then falls back to direct file lookup.
        Raises FileNotFoundError if not found.
        """
        # Try loading from registry first
        for record in self._load_registry():
            if record["id"] == app_id:
                path = record["file_path"]
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)

        # Fallback: construct path directly if registry is missing/corrupted
        fallback_path = os.path.join(DATA_DIR, f"{app_id}.json")
        if os.path.exists(fallback_path):
            with open(fallback_path, "r", encoding="utf-8") as f:
                return json.load(f)

        raise FileNotFoundError(f"No data found for app_id='{app_id}'")

    def list_apps(self) -> list[dict]:
        """
        Return all AppRecord dicts from the registry (newest first).
        Falls back to scanning data directory if registry is missing/corrupted.
        """
        records = self._load_registry()

        # Fallback: if registry is empty, scan directory
        if not records and os.path.exists(DATA_DIR):
            for filename in os.listdir(DATA_DIR):
                if filename == "registry.json" or not filename.endswith(".json"):
                    continue
                file_path = os.path.join(DATA_DIR, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    app_id = filename.replace(".json", "")
                    records.append(
                        {
                            "id": app_id,
                            "app_name": data.get("app_name", "unknown"),
                            "url": data.get("url", ""),
                            "tool_used": data.get("tool_used", ""),
                            "file_path": file_path,
                            "endpoint_count": len(data.get("endpoints", [])),
                        }
                    )
                except (json.JSONDecodeError, IOError):
                    pass

        return list(reversed(records))

    def delete(self, app_id: str) -> bool:
        """
        Remove the data file and registry entry for app_id.
        Returns True if something was actually deleted.
        """
        registry = self._load_registry()
        new_registry = []
        deleted = False

        for rec in registry:
            if rec["id"] == app_id:
                # Remove the data file
                fp = rec.get("file_path", "")
                if fp and os.path.exists(fp):
                    os.remove(fp)
                deleted = True
            else:
                new_registry.append(rec)

        if deleted:
            self._save_registry(new_registry)
        return deleted

    def get_record(self, app_id: str) -> dict | None:
        """
        Return a single AppRecord dict or None.
        Falls back to reconstructing record from data file if registry is missing.
        """
        for rec in self._load_registry():
            if rec["id"] == app_id:
                return rec

        # Fallback: reconstruct record from data file if registry is unavailable
        fallback_path = os.path.join(DATA_DIR, f"{app_id}.json")
        if os.path.exists(fallback_path):
            try:
                with open(fallback_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Reconstruct AppRecord from the data
                return {
                    "id": app_id,
                    "app_name": data.get("app_name", "unknown"),
                    "url": data.get("url", ""),
                    "tool_used": data.get("tool_used", ""),
                    "file_path": fallback_path,
                    "endpoint_count": len(data.get("endpoints", [])),
                }
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def rebuild_registry(self) -> int:
        """
        Scan data directory and rebuild registry from existing .json files.
        Useful for recovery if registry.json is corrupted.
        Returns the number of records rebuilt.
        """
        records = []
        if not os.path.exists(DATA_DIR):
            return 0

        for filename in os.listdir(DATA_DIR):
            if filename == "registry.json" or not filename.endswith(".json"):
                continue

            file_path = os.path.join(DATA_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                app_id = filename.replace(".json", "")
                record = {
                    "id": app_id,
                    "app_name": data.get("app_name", "unknown"),
                    "url": data.get("url", ""),
                    "tool_used": data.get("tool_used", ""),
                    "file_path": file_path,
                    "endpoint_count": len(data.get("endpoints", [])),
                }
                records.append(record)
            except (json.JSONDecodeError, IOError):
                pass

        self._save_registry(records)
        return len(records)

    # ── Private helpers ───────────────────────────────────────────────

    def _slugify(self, name: str) -> str:
        return re.sub(r"[^a-z0-9]", "_", name.lower())

    def _write_json(self, path: str, data: dict) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_registry(self) -> list[dict]:
        if not os.path.exists(REGISTRY_PATH):
            return []
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_registry(self, records: list[dict]) -> None:
        self._write_json(REGISTRY_PATH, records)

    def _upsert_registry(self, record: AppRecord) -> None:
        """Insert or update the record in the registry by id."""
        registry = self._load_registry()
        registry = [r for r in registry if r["id"] != record.id]
        from dataclasses import asdict

        registry.append(asdict(record))
        self._save_registry(registry)
