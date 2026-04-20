from typing import Literal

from pydantic import Field

from app.models.architect_models import ArchitectOutput
from app.models.api_models import APIOutput
from app.models.codegen_models import CodegenOutput
from app.models.frontend_models import FrontendOutput
from app.models.planner_models import PlannerOutput
from app.models.retrieval_models import RetrievalOutput
from app.models.review_models import ReviewOutput
from app.models.schema_models import SchemaOutput
from app.models.shared import StrictModel
from app.models.validation_models import ValidationSummary

RunStatus = Literal["pending", "queued", "running", "paused", "completed", "failed"]


class ArtifactManifest(StrictModel):
    files: list[str] = Field(default_factory=list)


class RunState(StrictModel):
    run_id: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    llm_backend: str = Field(default="fallback", min_length=1)
    llm_fallback_reason: str | None = None
    approval_required: bool = False
    approval_granted: bool = True
    retrieval_output: RetrievalOutput | None = None
    planner_output: PlannerOutput | None = None
    architect_output: ArchitectOutput | None = None
    schema_output: SchemaOutput | None = None
    api_output: APIOutput | None = None
    frontend_output: FrontendOutput | None = None
    codegen_output: CodegenOutput | None = None
    validation_summary: ValidationSummary | None = None
    review_output: ReviewOutput | None = None
    correction_count: int = 0
    llm_call_count: int = 0
    llm_estimated_input_tokens: int = 0
    llm_estimated_output_tokens: int = 0
    llm_estimated_cost_usd: float = 0.0
    governance_budget_exceeded: bool = False
    package_summary: dict[str, str | int | bool | None] = Field(default_factory=dict)
    completed_steps: list[str] = Field(default_factory=list)
    status: RunStatus = "pending"
    errors: list[str] = Field(default_factory=list)
    artifact_manifest: ArtifactManifest = Field(default_factory=ArtifactManifest)
