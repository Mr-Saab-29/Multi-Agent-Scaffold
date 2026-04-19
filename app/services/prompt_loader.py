from pathlib import Path


class PromptLoader:
    def __init__(self, prompts_root: Path):
        self._prompts_root = prompts_root

    def load(self, filename: str) -> str:
        path = self._prompts_root / filename
        return path.read_text(encoding="utf-8")
