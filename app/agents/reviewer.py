from app.models.review_models import ReviewIssue, ReviewOutput
from app.orchestrator.state import RunState
from app.services.artifact_store import ArtifactStore
from app.services.llm import LLMClient
from app.services.prompt_loader import PromptLoader


class ReviewerAgent:
    def __init__(self, llm_client: LLMClient, artifact_store: ArtifactStore, prompt_loader: PromptLoader):
        self._llm = llm_client
        self._store = artifact_store
        self._prompts = prompt_loader

    def run(self, state: RunState, filename: str = "07_review.json") -> ReviewOutput:
        system_prompt = self._prompts.load("reviewer.md")
        _ = self._llm.generate_json(system_prompt=system_prompt, user_prompt=state.user_prompt)

        issues: list[ReviewIssue] = []

        if state.validation_summary is not None:
            for err in state.validation_summary.errors:
                target = _target_from_code(err.code)
                issues.append(
                    ReviewIssue(
                        code=f"REVIEW_{err.code}",
                        severity="critical",
                        target_stage=target,
                        message=err.message,
                        suggested_fix=f"Rerun {target} with reviewer feedback and regenerate downstream artifacts.",
                    )
                )

        if state.api_output is not None:
            for group in state.api_output.route_groups:
                methods = {e.method.upper() for e in group.endpoints}
                if "POST" not in methods or "GET" not in methods:
                    issues.append(
                        ReviewIssue(
                            code="REVIEW_MISSING_CORE_ROUTES",
                            severity="critical",
                            target_stage="api",
                            message=f"Route group '{group.name}' is missing core list/create routes.",
                            suggested_fix="Add GET and POST routes for the entity.",
                        )
                    )

                if any(not e.auth_required for e in group.endpoints if e.method.upper() in {"POST", "PATCH", "DELETE"}):
                    issues.append(
                        ReviewIssue(
                            code="REVIEW_AUTH_GAP",
                            severity="critical",
                            target_stage="api",
                            message=f"Mutating routes in '{group.name}' have auth gaps.",
                            suggested_fix="Mark mutating endpoints as auth_required=True.",
                        )
                    )

        if state.frontend_output is not None and state.api_output is not None:
            known_paths = {e.path for g in state.api_output.route_groups for e in g.endpoints}
            for mapping in state.frontend_output.screen_api_mapping:
                if not mapping.endpoints:
                    issues.append(
                        ReviewIssue(
                            code="REVIEW_SCREEN_NO_BACKEND",
                            severity="medium",
                            target_stage="frontend",
                            message=f"Screen '{mapping.screen}' has no backend mapping.",
                            suggested_fix="Map the screen to at least one API endpoint.",
                        )
                    )
                for endpoint in mapping.endpoints:
                    path = endpoint.split(" ", 1)[1] if " " in endpoint else endpoint
                    if path not in known_paths and "{id}" not in path:
                        issues.append(
                            ReviewIssue(
                                code="REVIEW_UNKNOWN_MAPPING",
                                severity="critical",
                                target_stage="frontend",
                                message=f"Screen '{mapping.screen}' maps to unknown endpoint '{endpoint}'.",
                                suggested_fix="Align frontend mapping with API plan.",
                            )
                        )

        correction_needed = any(issue.severity == "critical" for issue in issues)
        summary = (
            f"Review completed with {len(issues)} issue(s). "
            f"Critical issues: {sum(1 for i in issues if i.severity == 'critical')}."
        )
        output = ReviewOutput(issues=issues, corrected_summary=summary, correction_needed=correction_needed)

        json_path = self._store.write_json_artifact(filename, output.model_dump())
        md_path = self._store.write_text_artifact(filename.replace(".json", ".md"), _to_markdown(output))
        self._store.append_manifest(json_path)
        self._store.append_manifest(md_path)
        return output


def _target_from_code(code: str) -> str:
    if code.startswith("SCHEMA"):
        return "schema"
    if code.startswith("API"):
        return "api"
    if code.startswith("UI"):
        return "frontend"
    return "validation"


def _to_markdown(output: ReviewOutput) -> str:
    lines = ["# Reviewer Report", "", output.corrected_summary, "", "## Issues"]
    if not output.issues:
        lines.append("- No issues detected.")
    else:
        for issue in output.issues:
            lines.append(
                f"- **{issue.severity.upper()}** `{issue.code}` ({issue.target_stage}): {issue.message} | Fix: {issue.suggested_fix}"
            )
    return "\n".join(lines) + "\n"
