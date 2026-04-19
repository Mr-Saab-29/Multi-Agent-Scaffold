from app.agents.reviewer import ReviewerAgent
from app.models.review_models import ReviewIssue, ReviewOutput
from app.orchestrator.runner import OrchestratorRunner


def test_orchestrator_runs_day3_pipeline() -> None:
    state = OrchestratorRunner().run("Build a booking tool for salons")
    assert state.status == "completed"
    assert state.review_output is not None
    assert state.package_summary
    assert state.completed_steps == [
        "planner",
        "retrieval",
        "architect",
        "schema",
        "api",
        "frontend",
        "codegen",
        "validation",
        "reviewer",
        "correction",
        "package_artifacts",
    ]


def test_correction_loop_runs_once(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_run(self, state, filename="07_review.json"):
        calls["count"] += 1
        if calls["count"] == 1:
            output = ReviewOutput(
                issues=[
                    ReviewIssue(
                        code="REVIEW_FORCE_CRITICAL",
                        severity="critical",
                        target_stage="api",
                        message="Force one correction pass",
                        suggested_fix="Regenerate api stage",
                    )
                ],
                corrected_summary="Critical issue found.",
                correction_needed=True,
            )
        else:
            output = ReviewOutput(issues=[], corrected_summary="Clean after correction.", correction_needed=False)

        path = self._store.write_json_artifact(filename, output.model_dump())
        self._store.append_manifest(path)
        return output

    monkeypatch.setattr(ReviewerAgent, "run", fake_run)

    state = OrchestratorRunner().run("Build an expense tracker")
    assert state.status == "completed"
    assert state.correction_count == 1
    assert any(path.endswith("04_api_corrected.json") for path in state.artifact_manifest.files)
    assert any(path.endswith("07_review_corrected.json") for path in state.artifact_manifest.files)
