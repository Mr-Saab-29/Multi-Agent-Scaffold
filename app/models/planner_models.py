from pydantic import Field

from app.models.shared import StrictModel


class RequirementItem(StrictModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class PlannerOutput(StrictModel):
    app_name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    goals: list[str] = Field(default_factory=list)
    requirements: list[RequirementItem] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
