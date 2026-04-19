from pydantic import Field

from app.models.shared import EntitySpec, RelationshipSpec, StrictModel


class ComponentSpec(StrictModel):
    name: str = Field(min_length=1)
    responsibility: str = Field(min_length=1)


class ArchitectOutput(StrictModel):
    architecture_style: str = Field(min_length=1)
    components: list[ComponentSpec] = Field(default_factory=list)
    data_entities: list[EntitySpec] = Field(default_factory=list)
    relationships: list[RelationshipSpec] = Field(default_factory=list)
    sequence_overview: list[str] = Field(default_factory=list)
