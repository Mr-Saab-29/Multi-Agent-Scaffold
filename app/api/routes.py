import logging
import json
from pathlib import Path
import time

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    ApprovalResponse,
    ArtifactContentResponse,
    ArtifactListResponse,
    AsyncRunSubmitResponse,
    RunStateResponse,
    ScaffoldRunRequest,
    ScaffoldRunResponse,
)
from app.orchestrator.async_manager import AsyncRunManager
from app.orchestrator.runner import OrchestratorRunner

router = APIRouter(prefix="/scaffold", tags=["scaffold"])
runner = OrchestratorRunner()
async_manager = AsyncRunManager(runner)
logger = logging.getLogger(__name__)


@router.post("/run", response_model=ScaffoldRunResponse)
def run_scaffold(req: ScaffoldRunRequest) -> ScaffoldRunResponse:
    if req.require_planner_approval:
        raise HTTPException(
            status_code=400,
            detail="Planner approval checkpoint is supported on /scaffold/run/async",
        )
    logger.info("Starting scaffold run for prompt length=%s", len(req.prompt))
    state = runner.run(user_prompt=req.prompt)
    logger.info("Completed scaffold run id=%s status=%s", state.run_id, state.status)
    return ScaffoldRunResponse(
        run_id=state.run_id,
        status=state.status,
        llm_backend=state.llm_backend,
        llm_fallback_reason=state.llm_fallback_reason,
        approval_required=state.approval_required,
        approval_granted=state.approval_granted,
        completed_steps=state.completed_steps,
        artifact_manifest=state.artifact_manifest.files,
        validation_summary=state.validation_summary,
        review_output=state.review_output,
        correction_count=state.correction_count,
        llm_call_count=state.llm_call_count,
        llm_estimated_input_tokens=state.llm_estimated_input_tokens,
        llm_estimated_output_tokens=state.llm_estimated_output_tokens,
        llm_estimated_cost_usd=state.llm_estimated_cost_usd,
        governance_budget_exceeded=state.governance_budget_exceeded,
        package_summary=state.package_summary,
        planner_summary=state.planner_output.summary if state.planner_output else None,
    )


@router.get("/run/{run_id}", response_model=RunStateResponse)
def get_run(run_id: str) -> RunStateResponse:
    state = runner.get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return RunStateResponse(state=state)


@router.post("/run/async", response_model=AsyncRunSubmitResponse)
def run_scaffold_async(req: ScaffoldRunRequest) -> AsyncRunSubmitResponse:
    run_id = async_manager.submit(
        prompt=req.prompt,
        require_planner_approval=req.require_planner_approval,
    )
    return AsyncRunSubmitResponse(
        run_id=run_id,
        status="paused" if req.require_planner_approval else "queued",
        approval_required=req.require_planner_approval,
    )


@router.post("/run/{run_id}/approve", response_model=ApprovalResponse)
def approve_run(run_id: str) -> ApprovalResponse:
    approved = async_manager.approve(run_id)
    if not approved:
        raise HTTPException(status_code=400, detail="Run is not awaiting approval or does not exist")
    return ApprovalResponse(run_id=run_id, approved=True)


@router.get("/run/{run_id}/events")
def stream_run_events(
    run_id: str,
    since: int = Query(default=0, ge=0),
) -> StreamingResponse:
    if not async_manager.has_run(run_id) and runner.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    def event_generator():
        cursor = since
        idle_ticks = 0
        while True:
            events = async_manager.events_since(run_id, cursor)
            if events:
                for event in events:
                    cursor = event["index"] + 1
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") == "run_finalized":
                        return
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks > 300:
                    return
                time.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/run/{run_id}/artifacts", response_model=ArtifactListResponse)
def list_artifacts(run_id: str) -> ArtifactListResponse:
    state = runner.get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return ArtifactListResponse(run_id=run_id, artifacts=state.artifact_manifest.files)


@router.get("/run/{run_id}/artifacts/content", response_model=ArtifactContentResponse)
def read_artifact_content(
    run_id: str,
    path: str = Query(min_length=1, description="Absolute artifact path from the manifest"),
) -> ArtifactContentResponse:
    state = runner.get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    if path not in state.artifact_manifest.files:
        raise HTTPException(status_code=404, detail="Artifact path is not part of this run manifest")

    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found on disk")
    if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".zip"}:
        raise HTTPException(status_code=400, detail="Binary file preview is not supported")

    content = file_path.read_text(encoding="utf-8", errors="replace")
    return ArtifactContentResponse(run_id=run_id, path=path, content=content)
