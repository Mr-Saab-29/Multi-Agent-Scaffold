from pathlib import Path

from app.core.config import Settings
from app.utils.json_io import read_json, write_json


class ArtifactStore:
    def __init__(self, settings: Settings, run_id: str):
        self._base_dir = settings.runs_path / run_id
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def write_json_artifact(self, filename: str, payload: dict) -> str:
        path = self._base_dir / filename
        write_json(path, payload)
        return str(path)

    def write_text_artifact(self, filename: str, content: str) -> str:
        path = self._base_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def read_manifest(self) -> dict:
        path = self._base_dir / "manifest.json"
        if path.exists():
            return read_json(path)
        return {"files": []}

    def append_manifest(self, file_path: str) -> dict:
        manifest = self.read_manifest()
        files = manifest.get("files", [])
        if file_path not in files:
            files.append(file_path)
        manifest_path = str(self._base_dir / "manifest.json")
        if manifest_path not in files:
            files.append(manifest_path)
        manifest["files"] = files
        self.write_json_artifact("manifest.json", manifest)
        return manifest
