from pydantic import Field

from app.models.review_models import ReviewOutput
from app.models.shared import StrictModel
from app.models.validation_models import ValidationSummary
from app.orchestrator.state import RunState


class ScaffoldRunRequest(StrictModel):
    prompt: str = Field(min_length=1, description="Natural language app prompt")
    require_planner_approval: bool = False


class ScaffoldRunResponse(StrictModel):
    run_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    llm_backend: str = Field(min_length=1)
    llm_fallback_reason: str | None = None
    approval_required: bool = False
    approval_granted: bool = True
    completed_steps: list[str] = Field(default_factory=list)
    artifact_manifest: list[str] = Field(default_factory=list)
    validation_summary: ValidationSummary | None = None
    review_output: ReviewOutput | None = None
    correction_count: int = 0
    llm_call_count: int = 0
    llm_estimated_input_tokens: int = 0
    llm_estimated_output_tokens: int = 0
    llm_estimated_cost_usd: float = 0.0
    governance_budget_exceeded: bool = False
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


class AsyncRunSubmitResponse(StrictModel):
    run_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    approval_required: bool = False


class ApprovalResponse(StrictModel):
    run_id: str = Field(min_length=1)
    approved: bool
