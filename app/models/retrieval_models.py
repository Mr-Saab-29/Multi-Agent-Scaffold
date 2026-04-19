from pydantic import Field

from app.models.shared import StrictModel


class RetrievedTemplate(StrictModel):
    path: str = Field(min_length=1)
    score: int = 0


class RetrievalOutput(StrictModel):
    query: str = Field(min_length=1)
    backend_templates: list[RetrievedTemplate] = Field(default_factory=list)
    frontend_templates: list[RetrievedTemplate] = Field(default_factory=list)
    examples: list[RetrievedTemplate] = Field(default_factory=list)
