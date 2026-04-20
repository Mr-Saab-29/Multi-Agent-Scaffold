import json
from typing import Any

import requests
import streamlit as st

DEFAULT_API_BASE = "http://127.0.0.1:8000"
PIPELINE_STEPS = [
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


def _api_get(base_url: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(f"{base_url}{path}", params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def _api_post(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{base_url}{path}", json=payload, timeout=1200)
    response.raise_for_status()
    return response.json()


def _render_pipeline_progress(completed_steps: list[str]) -> None:
    st.subheader("Pipeline Steps")
    for step in PIPELINE_STEPS:
        status = "✅" if step in completed_steps else "⏳"
        st.write(f"{status} {step}")


def _render_json_panel(title: str, data: Any) -> None:
    with st.expander(title, expanded=False):
        st.json(data)


def _artifact_panel(api_base: str, run_id: str, artifact_manifest: list[str]) -> None:
    st.subheader("Artifacts")
    if not artifact_manifest:
        st.info("No artifacts recorded.")
        return

    st.write(f"Total artifacts: {len(artifact_manifest)}")
    st.code("\n".join(artifact_manifest), language="text")

    selected = st.selectbox("Preview artifact", artifact_manifest, index=0)
    if st.button("Load Artifact Preview"):
        try:
            preview = _api_get(
                api_base,
                f"/scaffold/run/{run_id}/artifacts/content",
                params={"path": selected},
            )
            st.text_area("Artifact Content", value=preview["content"], height=300)
            st.download_button(
                label="Download Selected Artifact",
                data=preview["content"],
                file_name=selected.split("/")[-1],
                mime="text/plain",
            )
        except requests.HTTPError as exc:
            st.error(f"Failed to load artifact preview: {exc.response.text}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to load artifact preview: {exc}")


def main() -> None:
    st.set_page_config(page_title="Multi-Agent App Scaffolder", layout="wide")
    st.title("Multi-Agent App Scaffolder Demo")

    with st.sidebar:
        st.header("Backend")
        api_base = st.text_input("FastAPI Base URL", value=DEFAULT_API_BASE).rstrip("/")
        run_id_input = st.text_input("Load Existing Run ID (optional)", value="")

    prompt = st.text_area(
        "App Prompt",
        value="Build a marketplace app for local artisans with orders and reviews",
        height=120,
    )
    run_mode_async = st.checkbox("Use async run endpoint", value=False)
    require_planner_approval = st.checkbox("Require planner approval (async only)", value=False)

    col_run, col_refresh = st.columns(2)

    if "last_run_id" not in st.session_state:
        st.session_state["last_run_id"] = ""

    with col_run:
        if st.button("Run Scaffold"):
            if not prompt.strip():
                st.error("Prompt is required.")
            else:
                with st.spinner("Running full pipeline..."):
                    try:
                        if run_mode_async:
                            run_resp = _api_post(
                                api_base,
                                "/scaffold/run/async",
                                {
                                    "prompt": prompt.strip(),
                                    "require_planner_approval": require_planner_approval,
                                },
                            )
                        else:
                            run_resp = _api_post(api_base, "/scaffold/run", {"prompt": prompt.strip()})
                        st.session_state["last_run_id"] = run_resp["run_id"]
                        st.session_state["event_offset"] = 0
                        st.success(f"Run accepted: {run_resp['run_id']}")
                    except requests.HTTPError as exc:
                        st.error(f"Run failed: {exc.response.text}")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Run failed: {exc}")

    active_run_id = run_id_input.strip() or st.session_state.get("last_run_id", "")

    with col_refresh:
        if st.button("Refresh Run Data") and not active_run_id:
            st.warning("No run id available. Start a run or provide a run id.")

    if not active_run_id:
        st.info("Run a scaffold job or paste an existing run id to inspect outputs.")
        return

    st.caption(f"Inspecting run: `{active_run_id}`")

    if st.button("Approve Run (if paused)"):
        try:
            approve = _api_post(api_base, f"/scaffold/run/{active_run_id}/approve", {})
            st.success(f"Approval submitted: {approve}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Approval failed: {exc}")

    try:
        run_state_resp = _api_get(api_base, f"/scaffold/run/{active_run_id}")
        state = run_state_resp["state"]
    except requests.HTTPError as exc:
        st.error(f"Failed to fetch run state: {exc.response.text}")
        return
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to fetch run state: {exc}")
        return

    st.subheader("Run Summary")
    st.write(
        {
            "run_id": state.get("run_id"),
            "status": state.get("status"),
            "llm_backend": state.get("llm_backend"),
            "llm_fallback_reason": state.get("llm_fallback_reason"),
            "llm_call_count": state.get("llm_call_count"),
            "estimated_cost_usd": state.get("llm_estimated_cost_usd"),
            "governance_budget_exceeded": state.get("governance_budget_exceeded"),
            "correction_count": state.get("correction_count"),
        }
    )

    _render_pipeline_progress(state.get("completed_steps", []))

    if "event_offset" not in st.session_state:
        st.session_state["event_offset"] = 0
    if st.button("Fetch New Events"):
        try:
            events_resp = requests.get(
                f"{api_base}/scaffold/run/{active_run_id}/events",
                params={"since": st.session_state["event_offset"]},
                timeout=20,
            )
            if events_resp.ok:
                lines = [line[6:] for line in events_resp.text.splitlines() if line.startswith("data: ")]
                events = [json.loads(line) for line in lines if line.strip()]
                if events:
                    st.session_state["event_offset"] = events[-1]["index"] + 1
                st.write({"new_events": len(events), "events": events[-10:]})
            else:
                st.warning(f"Event fetch failed: {events_resp.text}")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Event fetch failed: {exc}")

    left, right = st.columns(2)
    with left:
        _render_json_panel("Planner Output", state.get("planner_output"))
        _render_json_panel("Architect Output", state.get("architect_output"))
        _render_json_panel("Schema Output", state.get("schema_output"))
        _render_json_panel("API Output", state.get("api_output"))
    with right:
        _render_json_panel("Frontend Output", state.get("frontend_output"))
        _render_json_panel("Codegen Output", state.get("codegen_output"))
        _render_json_panel("Reviewer Output", state.get("review_output"))
        _render_json_panel("Validation Summary", state.get("validation_summary"))

    package_summary = state.get("package_summary") or {}
    if package_summary:
        st.subheader("Package Summary")
        st.json(package_summary)

    manifest = (state.get("artifact_manifest") or {}).get("files", [])
    _artifact_panel(api_base, active_run_id, manifest)

    if state.get("errors"):
        st.subheader("Errors")
        st.code("\n\n".join(state["errors"]))


if __name__ == "__main__":
    main()
