from pathlib import Path

from app.agents.reviewer import ReviewerAgent
from app.core.config import Settings
from app.models.api_models import APIOutput, EndpointSpec, RouteGroupSpec
from app.models.review_models import ReviewOutput
from app.orchestrator.state import RunState
from app.services.artifact_store import ArtifactStore
from app.services.llm import LLMClient
from app.services.prompt_loader import PromptLoader


def test_reviewer_detects_auth_gap(tmp_path) -> None:
    settings = Settings(runs_dir=str(tmp_path), gemini_api_key=None)
    store = ArtifactStore(settings=settings, run_id="review-case")
    reviewer = ReviewerAgent(
        llm_client=LLMClient(settings),
        artifact_store=store,
        prompt_loader=PromptLoader(Path("prompts")),
    )

    state = RunState(run_id="review-case", user_prompt="Build admin app")
    state.api_output = APIOutput(
        route_groups=[
            RouteGroupSpec(
                name="users",
                base_path="/api/users",
                endpoints=[
                    EndpointSpec(method="POST", path="/api/users", summary="Create user", auth_required=False),
                ],
            )
        ],
        request_models=[],
        response_models=[],
        auth_requirements=[],
        validation_notes=[],
    )

    output = reviewer.run(state)
    assert isinstance(output, ReviewOutput)
    assert any(issue.code == "REVIEW_AUTH_GAP" for issue in output.issues)
    assert (tmp_path / "review-case" / "07_review.json").exists()
