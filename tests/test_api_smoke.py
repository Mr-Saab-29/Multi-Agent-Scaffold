from fastapi.testclient import TestClient

from app.main import app


def test_run_and_fetch() -> None:
    client = TestClient(app)

    run_resp = client.post("/scaffold/run", json={"prompt": "Build a task tracker for teams"})
    assert run_resp.status_code == 200
    run_body = run_resp.json()
    assert run_body["run_id"]
    assert run_body["status"] == "completed"
    assert run_body["llm_backend"] in {"gemini", "fallback"}
    assert "llm_fallback_reason" in run_body
    assert run_body["completed_steps"] == [
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
    assert run_body["validation_summary"] is not None
    assert run_body["review_output"] is not None
    assert "package_summary" in run_body
    assert "validation_results.json" in "\n".join(run_body["artifact_manifest"])
    assert "/generated/backend/routes/" in "\n".join(run_body["artifact_manifest"])
    assert "/generated/frontend/pages/" in "\n".join(run_body["artifact_manifest"])

    get_resp = client.get(f"/scaffold/run/{run_body['run_id']}")
    assert get_resp.status_code == 200
    state = get_resp.json()["state"]
    assert state["run_id"] == run_body["run_id"]
    assert state["llm_backend"] in {"gemini", "fallback"}
    assert state["api_output"] is not None
    assert state["frontend_output"] is not None
    assert state["codegen_output"] is not None

    artifacts_resp = client.get(f"/scaffold/run/{run_body['run_id']}/artifacts")
    assert artifacts_resp.status_code == 200
    artifacts = artifacts_resp.json()["artifacts"]
    assert artifacts

    content_resp = client.get(
        f"/scaffold/run/{run_body['run_id']}/artifacts/content",
        params={"path": artifacts[0]},
    )
    assert content_resp.status_code == 200
    assert "content" in content_resp.json()
