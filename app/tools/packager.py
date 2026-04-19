from pathlib import Path

from app.orchestrator.state import RunState
from app.services.artifact_store import ArtifactStore


class RunPackager:
    def __init__(self, artifact_store: ArtifactStore):
        self._store = artifact_store

    def package(self, state: RunState) -> dict:
        package_dir = self._store.base_dir / "package"
        package_dir.mkdir(parents=True, exist_ok=True)
        effective_status = "completed" if state.status == "running" and not state.errors else state.status
        effective_steps = (
            state.completed_steps + ["package_artifacts"]
            if "package_artifacts" not in state.completed_steps
            else state.completed_steps
        )

        manifest = {
            "run_id": state.run_id,
            "status": effective_status,
            "completed_steps": effective_steps,
            "artifact_count": len(state.artifact_manifest.files),
            "files": state.artifact_manifest.files,
        }
        summary = {
            "run_id": state.run_id,
            "prompt": state.user_prompt,
            "llm_backend": state.llm_backend,
            "llm_fallback_reason": state.llm_fallback_reason,
            "validation_passed": state.validation_summary.passed if state.validation_summary else None,
            "review_critical_issues": sum(
                1
                for issue in (state.review_output.issues if state.review_output else [])
                if issue.severity == "critical"
            ),
            "correction_passes": state.correction_count,
        }
        zip_ready = {
            "root": str(self._store.base_dir),
            "include": state.artifact_manifest.files,
            "exclude": [],
        }

        paths = {
            "final_manifest": str(package_dir / "final_manifest.json"),
            "summary": str(package_dir / "consolidated_summary.json"),
            "zip_manifest": str(package_dir / "zip_manifest.json"),
            "report": str(package_dir / "run_report.md"),
        }

        self._store.write_json_artifact(str(Path("package") / "final_manifest.json"), manifest)
        self._store.write_json_artifact(str(Path("package") / "consolidated_summary.json"), summary)
        self._store.write_json_artifact(str(Path("package") / "zip_manifest.json"), zip_ready)
        self._store.write_text_artifact(str(Path("package") / "run_report.md"), _to_report(summary, manifest))

        for path in paths.values():
            self._store.append_manifest(path)

        return {"paths": paths, "summary": summary}


def _to_report(summary: dict, manifest: dict) -> str:
    return (
        "# Run Report\n\n"
        f"Run ID: {summary['run_id']}\n\n"
        f"Status: {manifest['status']}\n\n"
        f"LLM backend: {summary['llm_backend']}\n\n"
        f"Correction passes: {summary['correction_passes']}\n\n"
        f"Validation passed: {summary['validation_passed']}\n\n"
        f"Total artifacts: {manifest['artifact_count']}\n"
    )
