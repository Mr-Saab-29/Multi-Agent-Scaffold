from pathlib import Path


class FileTreeBuilder:
    def __init__(self, root: Path):
        self._root = root

    def ensure_generated_tree(self) -> Path:
        generated_root = self._root / "generated"
        for rel in (
            "backend/routes",
            "backend/models",
            "frontend/pages",
            "frontend/components",
        ):
            (generated_root / rel).mkdir(parents=True, exist_ok=True)
        return generated_root
