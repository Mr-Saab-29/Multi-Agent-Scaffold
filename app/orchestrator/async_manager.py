import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.core.config import get_settings
from app.core.metrics import llm_calls_total, runs_total
from app.orchestrator.runner import OrchestratorRunner
from app.orchestrator.state import RunState
from app.services.artifact_store import ArtifactStore


class AsyncRunManager:
    def __init__(self, runner: OrchestratorRunner):
        self._runner = runner
        self._settings = get_settings()
        self._executor = ThreadPoolExecutor(max_workers=self._settings.async_max_workers)
        self._events: dict[str, list[dict]] = {}
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def submit(self, prompt: str, require_planner_approval: bool = False) -> str:
        run_id = self._runner.create_run_id()
        with self._lock:
            self._events[run_id] = []
            self._jobs[run_id] = {
                "prompt": prompt,
                "submitted_at": time.time(),
                "require_planner_approval": require_planner_approval,
                "status": "queued",
            }
        self._push_event(run_id, {"type": "queued", "run_id": run_id})

        if require_planner_approval:
            self._persist_paused_for_approval(run_id=run_id, prompt=prompt)
            with self._lock:
                self._jobs[run_id]["status"] = "paused"
            self._push_event(run_id, {"type": "paused_for_approval", "run_id": run_id})
        else:
            self._start_job(run_id)

        return run_id

    def approve(self, run_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(run_id)
            if job is None:
                return False
            if job.get("status") != "paused":
                return False
            job["status"] = "queued"

        self._push_event(run_id, {"type": "approval_granted", "run_id": run_id})
        self._start_job(run_id)
        return True

    def events_since(self, run_id: str, offset: int) -> list[dict]:
        with self._lock:
            events = self._events.get(run_id, [])
            return events[offset:]

    def has_run(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._jobs

    def _start_job(self, run_id: str) -> None:
        with self._lock:
            prompt = self._jobs[run_id]["prompt"]
            self._jobs[run_id]["status"] = "running"

        self._executor.submit(self._execute, run_id, prompt)

    def _execute(self, run_id: str, prompt: str) -> None:
        self._push_event(run_id, {"type": "run_started", "run_id": run_id})

        def callback(payload: dict) -> None:
            self._push_event(run_id, payload)

        state = self._runner.run(user_prompt=prompt, run_id=run_id, event_callback=callback)
        with self._lock:
            if run_id in self._jobs:
                self._jobs[run_id]["status"] = state.status

        runs_total.labels("async", state.status).inc()
        llm_calls_total.inc(state.llm_call_count)
        self._push_event(run_id, {"type": "run_finalized", "run_id": run_id, "status": state.status})

    def _persist_paused_for_approval(self, run_id: str, prompt: str) -> None:
        settings = get_settings()
        store = ArtifactStore(settings=settings, run_id=run_id)
        state = RunState(
            run_id=run_id,
            user_prompt=prompt,
            status="paused",
            approval_required=True,
            approval_granted=False,
        )
        run_state_path = store.write_json_artifact("run_state.json", state.model_dump(mode="json"))
        store.append_manifest(run_state_path)
        manifest_data = store.read_manifest()
        state.artifact_manifest.files = manifest_data.get("files", [])
        store.write_json_artifact("run_state.json", state.model_dump(mode="json"))

    def _push_event(self, run_id: str, payload: dict) -> None:
        with self._lock:
            events = self._events.setdefault(run_id, [])
            payload = {"index": len(events), **payload, "ts": time.time()}
            events.append(payload)
