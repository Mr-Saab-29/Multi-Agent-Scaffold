from pydantic import Field

from app.models.shared import EntitySpec, RelationshipSpec, StrictModel


class TableSpec(StrictModel):
    name: str = Field(min_length=1)
    columns: list[str] = Field(default_factory=list)


class SchemaOutput(StrictModel):
    dialect: str = Field(default="postgresql")
    tables: list[TableSpec] = Field(default_factory=list)
    entities: list[EntitySpec] = Field(default_factory=list)
    relationships: list[RelationshipSpec] = Field(default_factory=list)
    sql: str = Field(min_length=1)
