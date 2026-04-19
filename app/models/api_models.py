from pydantic import Field

from app.models.shared import StrictModel


class APIField(StrictModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    required: bool = True


class APIModelSpec(StrictModel):
    name: str = Field(min_length=1)
    fields: list[APIField] = Field(default_factory=list)


class EndpointSpec(StrictModel):
    method: str = Field(min_length=1)
    path: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    request_model: str | None = None
    response_model: str | None = None
    auth_required: bool = False


class RouteGroupSpec(StrictModel):
    name: str = Field(min_length=1)
    base_path: str = Field(min_length=1)
    endpoints: list[EndpointSpec] = Field(default_factory=list)


class APIOutput(StrictModel):
    route_groups: list[RouteGroupSpec] = Field(default_factory=list)
    request_models: list[APIModelSpec] = Field(default_factory=list)
    response_models: list[APIModelSpec] = Field(default_factory=list)
    auth_requirements: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)
