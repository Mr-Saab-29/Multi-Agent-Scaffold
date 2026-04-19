from pathlib import Path

from app.models.architect_models import ArchitectOutput, ComponentSpec
from app.models.planner_models import PlannerOutput
from app.models.shared import EntitySpec, FieldSpec, RelationshipSpec
from app.services.artifact_store import ArtifactStore
from app.services.llm import LLMClient


class ArchitectAgent:
    def __init__(self, llm_client: LLMClient, artifact_store: ArtifactStore, prompt_path: Path):
        self._llm = llm_client
        self._store = artifact_store
        self._prompt_path = prompt_path

    def run(self, planner_output: PlannerOutput) -> ArchitectOutput:
        system_prompt = self._prompt_path.read_text(encoding="utf-8")
        _ = self._llm.generate_json(system_prompt=system_prompt, user_prompt=planner_output.model_dump_json())

        entities = [
            EntitySpec(
                name="users",
                description="Application users",
                fields=[
                    FieldSpec(name="id", type="uuid", nullable=False, unique=True, description="Primary key"),
                    FieldSpec(name="email", type="varchar", nullable=False, unique=True, description="Unique email"),
                    FieldSpec(name="created_at", type="timestamp", nullable=False, unique=False, description="Creation time"),
                ],
            ),
            EntitySpec(
                name="projects",
                description="User-owned projects",
                fields=[
                    FieldSpec(name="id", type="uuid", nullable=False, unique=True, description="Primary key"),
                    FieldSpec(name="owner_id", type="uuid", nullable=False, unique=False, description="FK to users.id"),
                    FieldSpec(name="name", type="varchar", nullable=False, unique=False, description="Project name"),
                ],
            ),
        ]
        relationships = [
            RelationshipSpec(
                from_entity="users",
                to_entity="projects",
                relation_type="one_to_many",
                description="One user can own many projects",
            )
        ]

        output = ArchitectOutput(
            architecture_style="modular monolith",
            components=[
                ComponentSpec(name="api", responsibility="Expose HTTP endpoints and validation"),
                ComponentSpec(name="orchestrator", responsibility="Coordinate multi-agent generation workflow"),
                ComponentSpec(name="artifact_store", responsibility="Persist generated outputs to files"),
            ],
            data_entities=entities,
            relationships=relationships,
            sequence_overview=[
                "Receive prompt from API",
                "Planner produces requirements",
                "Architect defines components and data entities",
                "Schema agent emits SQL schema",
            ],
        )

        json_path = self._store.write_json_artifact("02_architect.json", output.model_dump())
        md_path = self._store.write_text_artifact("architecture.md", _to_architecture_markdown(output))
        self._store.append_manifest(json_path)
        self._store.append_manifest(md_path)
        return output


def _to_architecture_markdown(output: ArchitectOutput) -> str:
    lines = ["# Architecture", "", f"Style: **{output.architecture_style}**", "", "## Components"]
    lines.extend([f"- **{c.name}**: {c.responsibility}" for c in output.components])
    lines.append("")
    lines.append("## Entities")
    for entity in output.data_entities:
        lines.append(f"- **{entity.name}**: {entity.description}")
    lines.append("")
    lines.append("## Relationships")
    lines.extend([f"- {r.from_entity} -> {r.to_entity} ({r.relation_type})" for r in output.relationships])
    return "\n".join(lines) + "\n"
