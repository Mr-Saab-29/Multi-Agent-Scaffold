from app.models.api_models import APIOutput
from app.models.frontend_models import ComponentSpec, FrontendOutput, ScreenAPIMap, ScreenSpec, UserFlowSpec
from app.models.planner_models import PlannerOutput
from app.models.retrieval_models import RetrievalOutput
from app.services.artifact_store import ArtifactStore
from app.services.llm import LLMClient
from app.services.prompt_loader import PromptLoader


class FrontendAgent:
    def __init__(self, llm_client: LLMClient, artifact_store: ArtifactStore, prompt_loader: PromptLoader):
        self._llm = llm_client
        self._store = artifact_store
        self._prompts = prompt_loader

    def run(
        self,
        planner_output: PlannerOutput,
        api_output: APIOutput,
        retrieval_output: RetrievalOutput,
        reviewer_feedback: list[str] | None = None,
        artifact_prefix: str = "05_frontend",
        model_override: str | None = None,
    ) -> FrontendOutput:
        system_prompt = self._prompts.load("frontend_agent.md")
        _ = self._llm.generate_json(
            system_prompt=system_prompt,
            user_prompt=planner_output.model_dump_json(),
            model=model_override,
        )

        screens = [
            ScreenSpec(
                name="Dashboard",
                path="/",
                description=f"Overview screen for {planner_output.app_name}",
                components=["TopNav", "SummaryCards", "RecentActivityList"],
            )
        ]
        mappings: list[ScreenAPIMap] = []

        for group in api_output.route_groups:
            singular = group.name[:-1] if group.name.endswith("s") else group.name
            screen_name = f"{singular.capitalize()}List"
            screen_path = f"/{group.name}"
            screens.append(
                ScreenSpec(
                    name=screen_name,
                    path=screen_path,
                    description=f"List and manage {group.name}",
                    components=[f"{singular.capitalize()}Table", "FilterBar", "PrimaryButton"],
                )
            )
            mappings.append(
                ScreenAPIMap(
                    screen=screen_name,
                    endpoints=[
                        f"GET {group.base_path}",
                        f"POST {group.base_path}",
                        f"PATCH {group.base_path}/{{id}}",
                    ],
                )
            )

        output = FrontendOutput(
            screens=screens,
            components=[
                ComponentSpec(name="TopNav", purpose="Primary navigation"),
                ComponentSpec(name="SummaryCards", purpose="At-a-glance KPIs"),
                ComponentSpec(name="PrimaryButton", purpose="Main call-to-action button"),
            ],
            user_flows=[
                UserFlowSpec(name="Create and edit record", steps=["Open list page", "Create new record", "Edit existing record"]),
                UserFlowSpec(name="Review dashboard", steps=["Open dashboard", "Inspect KPIs", "Navigate to details"]),
            ],
            screen_api_mapping=mappings,
        )

        if reviewer_feedback:
            # Preserve deterministic behavior while making correction intent explicit.
            output.user_flows.append(
                UserFlowSpec(name="Reviewer correction notes", steps=reviewer_feedback),
            )

        json_path = self._store.write_json_artifact(f"{artifact_prefix}.json", output.model_dump())
        md_path = self._store.write_text_artifact(
            "frontend_plan_corrected.md" if artifact_prefix != "05_frontend" else "frontend_plan.md",
            _to_markdown(output, retrieval_output),
        )
        self._store.append_manifest(json_path)
        self._store.append_manifest(md_path)
        return output


def _to_markdown(output: FrontendOutput, retrieval_output: RetrievalOutput) -> str:
    lines = ["# Frontend Plan", "", "## Screens"]
    lines.extend([f"- **{s.name}** ({s.path}): {s.description}" for s in output.screens])
    lines.append("")
    lines.append("## User Flows")
    lines.extend([f"- **{f.name}**: {' -> '.join(f.steps)}" for f in output.user_flows])
    lines.append("")
    lines.append("## Template References")
    lines.append(
        "- Frontend templates: "
        + (", ".join(t.path for t in retrieval_output.frontend_templates) if retrieval_output.frontend_templates else "none")
    )
    return "\n".join(lines) + "\n"
