from pydantic import Field

from app.models.shared import StrictModel


class GeneratedFileSpec(StrictModel):
    path: str = Field(min_length=1)
    language: str = Field(min_length=1)
    description: str = Field(min_length=1)


class CodegenOutput(StrictModel):
    generated_root: str = Field(min_length=1)
    backend_files: list[GeneratedFileSpec] = Field(default_factory=list)
    frontend_files: list[GeneratedFileSpec] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
