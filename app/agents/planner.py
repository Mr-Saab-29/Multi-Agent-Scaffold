from pathlib import Path

from app.models.planner_models import PlannerOutput, RequirementItem
from app.services.artifact_store import ArtifactStore
from app.services.llm import LLMClient


class PlannerAgent:
    def __init__(self, llm_client: LLMClient, artifact_store: ArtifactStore, prompt_path: Path):
        self._llm = llm_client
        self._store = artifact_store
        self._prompt_path = prompt_path

    def run(self, user_prompt: str, model_override: str | None = None) -> PlannerOutput:
        system_prompt = self._prompt_path.read_text(encoding="utf-8")
        _ = self._llm.generate_json(system_prompt=system_prompt, user_prompt=user_prompt, model=model_override)

        app_name = _extract_app_name(user_prompt)
        requirements = [
            RequirementItem(id="REQ-001", title="Core API", detail="Expose API endpoints for primary workflow."),
            RequirementItem(id="REQ-002", title="Data Model", detail="Define typed entities and relationships."),
            RequirementItem(id="REQ-003", title="Run Outputs", detail="Persist artifacts for each generation step."),
        ]

        output = PlannerOutput(
            app_name=app_name,
            summary=f"Plan for {app_name} generated from user prompt.",
            goals=[
                "Capture core product scope",
                "Define MVP constraints",
                "Prepare architecture input",
            ],
            requirements=requirements,
            assumptions=["MVP backend-first", "Single-tenant in initial version"],
            non_goals=["No frontend for Day 1", "No production deployment setup"],
        )

        json_path = self._store.write_json_artifact("01_planner.json", output.model_dump())
        md_body = _to_requirements_markdown(output)
        md_path = self._store.write_text_artifact("requirements.md", md_body)
        self._store.append_manifest(json_path)
        self._store.append_manifest(md_path)
        return output


def _extract_app_name(prompt: str) -> str:
    words = [w.strip(" ,.;:!?") for w in prompt.split() if w.strip(" ,.;:!?")]
    if not words:
        return "Generated App"
    return " ".join(words[:3]).title()


def _to_requirements_markdown(output: PlannerOutput) -> str:
    lines = [f"# {output.app_name} - Requirements", "", f"{output.summary}", "", "## Goals"]
    lines.extend([f"- {g}" for g in output.goals])
    lines.append("")
    lines.append("## Requirements")
    lines.extend([f"- **{r.id} {r.title}**: {r.detail}" for r in output.requirements])
    lines.append("")
    lines.append("## Assumptions")
    lines.extend([f"- {a}" for a in output.assumptions])
    lines.append("")
    lines.append("## Non-goals")
    lines.extend([f"- {n}" for n in output.non_goals])
    return "\n".join(lines) + "\n"
