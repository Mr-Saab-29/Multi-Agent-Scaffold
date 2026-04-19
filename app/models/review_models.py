from typing import Literal

from pydantic import Field

from app.models.shared import StrictModel

IssueSeverity = Literal["low", "medium", "critical"]


class ReviewIssue(StrictModel):
    code: str = Field(min_length=1)
    severity: IssueSeverity
    target_stage: str = Field(min_length=1)
    message: str = Field(min_length=1)
    suggested_fix: str = Field(min_length=1)


class ReviewOutput(StrictModel):
    issues: list[ReviewIssue] = Field(default_factory=list)
    corrected_summary: str = Field(min_length=1)
    correction_needed: bool = False
