import hashlib
import json
from pathlib import Path
from typing import Any


class StageCache:
    def __init__(self, cache_root: Path):
        self._cache_root = cache_root
        self._cache_root.mkdir(parents=True, exist_ok=True)

    def make_key(self, stage: str, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        digest = hashlib.sha256(f"{stage}:{canonical}".encode("utf-8")).hexdigest()
        return digest

    def get(self, stage: str, key: str) -> dict[str, Any] | None:
        path = self._path(stage, key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, stage: str, key: str, value: dict[str, Any]) -> None:
        path = self._path(stage, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=True), encoding="utf-8")

    def _path(self, stage: str, key: str) -> Path:
        return self._cache_root / stage / f"{key}.json"
