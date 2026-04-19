import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.orchestrator.runner import OrchestratorRunner


if __name__ == "__main__":
    prompt = "Build a CRM app for freelancers to manage contacts, deals, and tasks"
    runner = OrchestratorRunner()
    state = runner.run(prompt)

    payload = {
        "run_id": state.run_id,
        "status": state.status,
        "completed_steps": state.completed_steps,
        "artifact_manifest": state.artifact_manifest.files,
        "validation_passed": state.validation_summary.passed if state.validation_summary else None,
        "review_issues": len(state.review_output.issues) if state.review_output else 0,
    }
    print(json.dumps(payload, indent=2))
