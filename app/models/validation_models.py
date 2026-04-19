from pydantic import Field

from app.models.shared import StrictModel


class ValidationIssue(StrictModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ValidationSummary(StrictModel):
    passed: bool = True
    checks_run: list[str] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    errors: list[ValidationIssue] = Field(default_factory=list)
