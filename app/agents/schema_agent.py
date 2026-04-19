from pathlib import Path

from app.models.architect_models import ArchitectOutput
from app.models.schema_models import SchemaOutput, TableSpec
from app.services.artifact_store import ArtifactStore
from app.services.llm import LLMClient


class SchemaAgent:
    def __init__(self, llm_client: LLMClient, artifact_store: ArtifactStore, prompt_path: Path):
        self._llm = llm_client
        self._store = artifact_store
        self._prompt_path = prompt_path

    def run(self, architect_output: ArchitectOutput, model_override: str | None = None) -> SchemaOutput:
        system_prompt = self._prompt_path.read_text(encoding="utf-8")
        _ = self._llm.generate_json(
            system_prompt=system_prompt,
            user_prompt=architect_output.model_dump_json(),
            model=model_override,
        )

        sql = _to_sql(architect_output)
        tables = [
            TableSpec(
                name=entity.name,
                columns=[
                    f"{field.name} {field.type}{' NOT NULL' if not field.nullable else ''}"
                    for field in entity.fields
                ],
            )
            for entity in architect_output.data_entities
        ]

        output = SchemaOutput(
            dialect="postgresql",
            tables=tables,
            entities=architect_output.data_entities,
            relationships=architect_output.relationships,
            sql=sql,
        )

        json_path = self._store.write_json_artifact("03_schema.json", output.model_dump())
        sql_path = self._store.write_text_artifact("schema.sql", output.sql)
        self._store.append_manifest(json_path)
        self._store.append_manifest(sql_path)
        return output


def _to_sql(architect_output: ArchitectOutput) -> str:
    stmts: list[str] = []
    for entity in architect_output.data_entities:
        cols: list[str] = []
        for field in entity.fields:
            line = f"{field.name} {field.type}"
            if not field.nullable:
                line += " NOT NULL"
            if field.unique:
                line += " UNIQUE"
            if field.name == "id":
                line += " PRIMARY KEY"
            cols.append(line)
        stmts.append(f"CREATE TABLE {entity.name} (\n  " + ",\n  ".join(cols) + "\n);")

    for rel in architect_output.relationships:
        if rel.relation_type == "one_to_many":
            child = rel.to_entity
            parent = rel.from_entity
            fk_name = f"fk_{child}_{parent}"
            stmts.append(
                f"ALTER TABLE {child} ADD CONSTRAINT {fk_name} FOREIGN KEY (owner_id) REFERENCES {parent}(id);"
            )

    return "\n\n".join(stmts) + "\n"
