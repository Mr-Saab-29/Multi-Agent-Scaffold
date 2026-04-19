from pydantic import Field

from app.models.review_models import ReviewOutput
from app.models.shared import StrictModel
from app.models.validation_models import ValidationSummary
from app.orchestrator.state import RunState


class ScaffoldRunRequest(StrictModel):
    prompt: str = Field(min_length=1, description="Natural language app prompt")


class ScaffoldRunResponse(StrictModel):
    run_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    llm_backend: str = Field(min_length=1)
    llm_fallback_reason: str | None = None
    completed_steps: list[str] = Field(default_factory=list)
    artifact_manifest: list[str] = Field(default_factory=list)
    validation_summary: ValidationSummary | None = None
    review_output: ReviewOutput | None = None
    correction_count: int = 0
    package_summary: dict[str, str | int | bool | None] = Field(default_factory=dict)
    planner_summary: str | None = None


class RunStateResponse(StrictModel):
    state: RunState


class ArtifactListResponse(StrictModel):
    run_id: str = Field(min_length=1)
    artifacts: list[str] = Field(default_factory=list)


class ArtifactContentResponse(StrictModel):
    run_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    content: str = Field(min_length=1)
