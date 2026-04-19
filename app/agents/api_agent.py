from app.models.api_models import APIField, APIModelSpec, APIOutput, EndpointSpec, RouteGroupSpec
from app.models.architect_models import ArchitectOutput
from app.models.retrieval_models import RetrievalOutput
from app.models.schema_models import SchemaOutput
from app.services.artifact_store import ArtifactStore
from app.services.llm import LLMClient
from app.services.prompt_loader import PromptLoader


class APIAgent:
    def __init__(self, llm_client: LLMClient, artifact_store: ArtifactStore, prompt_loader: PromptLoader):
        self._llm = llm_client
        self._store = artifact_store
        self._prompts = prompt_loader

    def run(
        self,
        architect_output: ArchitectOutput,
        schema_output: SchemaOutput,
        retrieval_output: RetrievalOutput,
        reviewer_feedback: list[str] | None = None,
        artifact_prefix: str = "04_api",
        model_override: str | None = None,
    ) -> APIOutput:
        system_prompt = self._prompts.load("api_agent.md")
        _ = self._llm.generate_json(
            system_prompt=system_prompt,
            user_prompt=architect_output.model_dump_json(),
            model=model_override,
        )

        route_groups: list[RouteGroupSpec] = []
        request_models: list[APIModelSpec] = []
        response_models: list[APIModelSpec] = []

        for entity in architect_output.data_entities:
            base_path = f"/api/{entity.name}"
            model_name = _to_model_name(entity.name)
            request_model = APIModelSpec(
                name=f"{model_name}CreateRequest",
                fields=[
                    APIField(name=f.name, type=f.type, required=not f.nullable)
                    for f in entity.fields
                    if f.name != "id"
                ],
            )
            response_model = APIModelSpec(
                name=f"{model_name}Response",
                fields=[APIField(name=f.name, type=f.type, required=not f.nullable) for f in entity.fields],
            )

            endpoints = [
                EndpointSpec(
                    method="POST",
                    path=base_path,
                    summary=f"Create {entity.name}",
                    request_model=request_model.name,
                    response_model=response_model.name,
                    auth_required=True,
                ),
                EndpointSpec(
                    method="GET",
                    path=base_path,
                    summary=f"List {entity.name}",
                    response_model=f"list[{response_model.name}]",
                    auth_required=True,
                ),
                EndpointSpec(
                    method="GET",
                    path=f"{base_path}/{{id}}",
                    summary=f"Get {entity.name} by id",
                    response_model=response_model.name,
                    auth_required=True,
                ),
                EndpointSpec(
                    method="PATCH",
                    path=f"{base_path}/{{id}}",
                    summary=f"Update {entity.name}",
                    request_model=request_model.name,
                    response_model=response_model.name,
                    auth_required=True,
                ),
                EndpointSpec(
                    method="DELETE",
                    path=f"{base_path}/{{id}}",
                    summary=f"Delete {entity.name}",
                    auth_required=True,
                ),
            ]
            route_groups.append(RouteGroupSpec(name=entity.name, base_path=base_path, endpoints=endpoints))
            request_models.append(request_model)
            response_models.append(response_model)

        output = APIOutput(
            route_groups=route_groups,
            request_models=request_models,
            response_models=response_models,
            auth_requirements=["Bearer token for all mutating operations", "Role-based access can be added later"],
            validation_notes=[
                f"Designed from schema dialect: {schema_output.dialect}",
                f"Retrieved backend templates: {', '.join(t.path for t in retrieval_output.backend_templates) or 'none'}",
                f"Reviewer feedback: {' | '.join(reviewer_feedback) if reviewer_feedback else 'none'}",
            ],
        )

        json_path = self._store.write_json_artifact(f"{artifact_prefix}.json", output.model_dump())
        md_path = self._store.write_text_artifact(
            "api_plan_corrected.md" if artifact_prefix != "04_api" else "api_plan.md",
            _to_markdown(output),
        )
        self._store.append_manifest(json_path)
        self._store.append_manifest(md_path)
        return output


def _to_model_name(entity_name: str) -> str:
    cleaned = entity_name[:-1] if entity_name.endswith("s") and len(entity_name) > 1 else entity_name
    return "".join(part.capitalize() for part in cleaned.split("_"))


def _to_markdown(output: APIOutput) -> str:
    lines = ["# API Plan", "", "## Route Groups"]
    for group in output.route_groups:
        lines.append(f"- **{group.name}** ({group.base_path})")
        for ep in group.endpoints:
            lines.append(f"  - {ep.method} {ep.path}: {ep.summary}")
    lines.append("")
    lines.append("## Auth Requirements")
    lines.extend([f"- {req}" for req in output.auth_requirements])
    lines.append("")
    lines.append("## Validation Notes")
    lines.extend([f"- {note}" for note in output.validation_notes])
    return "\n".join(lines) + "\n"
