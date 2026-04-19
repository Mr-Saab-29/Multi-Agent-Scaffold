from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FieldSpec(StrictModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    nullable: bool = False
    unique: bool = False
    description: str = ""


class EntitySpec(StrictModel):
    name: str = Field(min_length=1)
    description: str = ""
    fields: list[FieldSpec] = Field(default_factory=list)


class RelationshipSpec(StrictModel):
    from_entity: str = Field(min_length=1)
    to_entity: str = Field(min_length=1)
    relation_type: str = Field(min_length=1, description="one_to_one | one_to_many | many_to_many")
    description: str = ""
