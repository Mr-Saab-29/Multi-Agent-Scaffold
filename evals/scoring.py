from app.orchestrator.state import RunState


def entity_coverage_score(state: RunState) -> float:
    if state.architect_output is None or state.schema_output is None:
        return 0.0
    entities = {e.name for e in state.architect_output.data_entities}
    tables = {t.name for t in state.schema_output.tables}
    if not entities:
        return 0.0
    return 100.0 * len(entities & tables) / len(entities)


def schema_consistency_score(state: RunState) -> float:
    if state.validation_summary is None:
        return 0.0
    schema_errors = [e for e in state.validation_summary.errors if e.code.startswith("SCHEMA")]
    return 100.0 if not schema_errors else max(0.0, 100.0 - 25.0 * len(schema_errors))


def route_completeness_score(state: RunState) -> float:
    if state.api_output is None:
        return 0.0
    scores: list[float] = []
    for group in state.api_output.route_groups:
        methods = {e.method.upper() for e in group.endpoints}
        need = {"GET", "POST", "PATCH", "DELETE"}
        scores.append(100.0 * len(methods & need) / len(need))
    return sum(scores) / len(scores) if scores else 0.0


def frontend_backend_alignment_score(state: RunState) -> float:
    if state.frontend_output is None or state.api_output is None:
        return 0.0
    known = {f"{e.method.upper()} {e.path}" for g in state.api_output.route_groups for e in g.endpoints}
    mapped = [ep for m in state.frontend_output.screen_api_mapping for ep in m.endpoints]
    if not mapped:
        return 0.0
    hits = sum(1 for ep in mapped if ep in known)
    return 100.0 * hits / len(mapped)


def artifact_generation_success_score(state: RunState) -> float:
    required = {
        "01_planner.json",
        "retrieval.json",
        "02_architect.json",
        "03_schema.json",
        "04_api.json",
        "05_frontend.json",
        "06_codegen.json",
        "validation_results.json",
    }
    files = set(state.artifact_manifest.files)
    hits = sum(1 for name in required if any(path.endswith(name) for path in files))
    return 100.0 * hits / len(required)


def issue_detection_coverage_score(state: RunState) -> float:
    if state.review_output is None:
        return 0.0
    # Reviewer participating with structured output is the core criteria here.
    return 100.0 if state.review_output.corrected_summary else 0.0


def score_case(state: RunState) -> dict[str, float]:
    scores = {
        "entity_coverage": entity_coverage_score(state),
        "schema_consistency": schema_consistency_score(state),
        "route_completeness": route_completeness_score(state),
        "frontend_backend_alignment": frontend_backend_alignment_score(state),
        "artifact_generation_success": artifact_generation_success_score(state),
        "issue_detection_coverage": issue_detection_coverage_score(state),
    }
    scores["overall"] = sum(scores.values()) / len(scores)
    return scores
