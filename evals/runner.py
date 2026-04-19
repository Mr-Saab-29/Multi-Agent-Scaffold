import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.orchestrator.runner import OrchestratorRunner
from evals.scoring import score_case


def run_evals(cases_path: Path | None = None) -> dict:
    path = cases_path or Path("evals/cases.json")
    cases = json.loads(path.read_text(encoding="utf-8"))
    runner = OrchestratorRunner()

    results = []
    for case in cases:
        state = runner.run(case["prompt"])
        scores = score_case(state)
        results.append(
            {
                "id": case["id"],
                "run_id": state.run_id,
                "status": state.status,
                "scores": scores,
            }
        )

    overall = sum(item["scores"]["overall"] for item in results) / len(results) if results else 0.0
    report = {
        "cases": results,
        "overall_score": overall,
        "case_count": len(results),
    }

    output_path = Path("evals/report.json")
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    report = run_evals()
    print(json.dumps(report, indent=2))
