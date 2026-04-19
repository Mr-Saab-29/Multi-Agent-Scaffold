from pydantic import Field

from app.models.shared import StrictModel


class ComponentSpec(StrictModel):
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class ScreenSpec(StrictModel):
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    description: str = Field(min_length=1)
    components: list[str] = Field(default_factory=list)


class UserFlowSpec(StrictModel):
    name: str = Field(min_length=1)
    steps: list[str] = Field(default_factory=list)


class ScreenAPIMap(StrictModel):
    screen: str = Field(min_length=1)
    endpoints: list[str] = Field(default_factory=list)


class FrontendOutput(StrictModel):
    screens: list[ScreenSpec] = Field(default_factory=list)
    components: list[ComponentSpec] = Field(default_factory=list)
    user_flows: list[UserFlowSpec] = Field(default_factory=list)
    screen_api_mapping: list[ScreenAPIMap] = Field(default_factory=list)
