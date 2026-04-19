from pathlib import Path

from app.models.retrieval_models import RetrievalOutput, RetrievedTemplate


class LocalTemplateRetriever:
    def __init__(self, knowledge_root: Path):
        self._knowledge_root = knowledge_root

    def retrieve(self, query: str, top_k: int = 3) -> RetrievalOutput:
        tokens = {tok.lower() for tok in query.split() if tok.strip()}
        backend = self._score_directory(self._knowledge_root / "templates" / "backend", tokens, top_k)
        frontend = self._score_directory(self._knowledge_root / "templates" / "frontend", tokens, top_k)
        examples = self._score_directory(self._knowledge_root / "examples", tokens, top_k)
        return RetrievalOutput(query=query, backend_templates=backend, frontend_templates=frontend, examples=examples)

    def _score_directory(self, directory: Path, tokens: set[str], top_k: int) -> list[RetrievedTemplate]:
        if not directory.exists():
            return []
        scored: list[tuple[int, Path]] = []
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            score = sum(1 for token in tokens if token in text or token in path.name.lower())
            scored.append((score, path))
        scored.sort(key=lambda x: (-x[0], str(x[1])))

        results: list[RetrievedTemplate] = []
        for score, path in scored[:top_k]:
            results.append(RetrievedTemplate(path=str(path), score=score))
        return results
