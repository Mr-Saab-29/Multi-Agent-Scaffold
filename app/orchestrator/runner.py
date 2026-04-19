import traceback
from pathlib import Path
from uuid import uuid4

from app.agents.api_agent import APIAgent
from app.agents.architect import ArchitectAgent, _to_architecture_markdown
from app.agents.codegen import CodegenAgent
from app.agents.frontend_agent import FrontendAgent
from app.agents.planner import PlannerAgent, _to_requirements_markdown
from app.agents.reviewer import ReviewerAgent
from app.agents.schema_agent import SchemaAgent
from app.core.config import get_settings
from app.models.architect_models import ArchitectOutput
from app.models.planner_models import PlannerOutput
from app.models.review_models import ReviewOutput
from app.models.schema_models import SchemaOutput
from app.models.validation_models import ValidationSummary
from app.orchestrator.graph import day2_graph
from app.orchestrator.state import ArtifactManifest, RunState
from app.services.artifact_store import ArtifactStore
from app.services.llm import LLMClient
from app.services.prompt_loader import PromptLoader
from app.services.stage_cache import StageCache
from app.tools.api_checker import APIChecker
from app.tools.packager import RunPackager
from app.tools.retrieval import LocalTemplateRetriever
from app.tools.schema_validator import SchemaValidator
from app.tools.ui_mapper import FrontendBackendMapper


class OrchestratorRunner:
    def __init__(self):
        self._settings = get_settings()

    def create_run_id(self) -> str:
        return uuid4().hex

    def run(self, user_prompt: str, run_id: str | None = None) -> RunState:
        resolved_run_id = run_id or self.create_run_id()
        state = RunState(run_id=resolved_run_id, user_prompt=user_prompt, status="running")
        store = ArtifactStore(settings=self._settings, run_id=resolved_run_id)
        llm_client = LLMClient(self._settings)
        state.llm_backend = llm_client.backend
        state.llm_fallback_reason = llm_client.fallback_reason

        prompts_dir = Path("prompts")
        prompt_loader = PromptLoader(prompts_dir)
        knowledge_root = Path("knowledge")
        stage_cache = StageCache(self._settings.runs_path / "_cache")

        planner = PlannerAgent(llm_client=llm_client, artifact_store=store, prompt_path=prompts_dir / "planner.md")
        architect = ArchitectAgent(llm_client=llm_client, artifact_store=store, prompt_path=prompts_dir / "architect.md")
        schema = SchemaAgent(llm_client=llm_client, artifact_store=store, prompt_path=prompts_dir / "schema_agent.md")
        api_agent = APIAgent(llm_client=llm_client, artifact_store=store, prompt_loader=prompt_loader)
        frontend_agent = FrontendAgent(llm_client=llm_client, artifact_store=store, prompt_loader=prompt_loader)
        codegen_agent = CodegenAgent(artifact_store=store)
        reviewer = ReviewerAgent(llm_client=llm_client, artifact_store=store, prompt_loader=prompt_loader)

        retriever = LocalTemplateRetriever(knowledge_root=knowledge_root)
        schema_validator = SchemaValidator()
        api_checker = APIChecker()
        ui_mapper = FrontendBackendMapper()
        packager = RunPackager(artifact_store=store)

        try:
            for node in day2_graph():
                if node == "planner":
                    planner_prompt = (prompts_dir / "planner.md").read_text(encoding="utf-8")
                    planner_model = self._stage_model("planner")
                    if self._settings.smart_enable_stage_cache:
                        planner_key = stage_cache.make_key(
                            "planner",
                            {"prompt": state.user_prompt, "template": planner_prompt, "model": planner_model},
                        )
                        cached = stage_cache.get("planner", planner_key)
                        if cached is not None:
                            state.planner_output = PlannerOutput.model_validate(cached)
                            self._persist_planner_artifacts(store, state.planner_output)
                        else:
                            state.planner_output = planner.run(state.user_prompt, model_override=planner_model)
                            stage_cache.set("planner", planner_key, state.planner_output.model_dump())
                    else:
                        state.planner_output = planner.run(state.user_prompt, model_override=planner_model)
                elif node == "retrieval":
                    state.retrieval_output = retriever.retrieve(state.user_prompt)
                    path = store.write_json_artifact("retrieval.json", state.retrieval_output.model_dump())
                    store.append_manifest(path)
                elif node == "architect":
                    if state.planner_output is None:
                        raise ValueError("Planner output missing")
                    architect_prompt = (prompts_dir / "architect.md").read_text(encoding="utf-8")
                    architect_model = self._stage_model("architect")
                    if self._settings.smart_enable_stage_cache:
                        architect_key = stage_cache.make_key(
                            "architect",
                            {
                                "planner_output": state.planner_output.model_dump(mode="json"),
                                "template": architect_prompt,
                                "model": architect_model,
                            },
                        )
                        cached = stage_cache.get("architect", architect_key)
                        if cached is not None:
                            state.architect_output = ArchitectOutput.model_validate(cached)
                            self._persist_architect_artifacts(store, state.architect_output)
                        else:
                            state.architect_output = architect.run(state.planner_output, model_override=architect_model)
                            stage_cache.set("architect", architect_key, state.architect_output.model_dump())
                    else:
                        state.architect_output = architect.run(state.planner_output, model_override=architect_model)
                elif node == "schema":
                    if state.architect_output is None:
                        raise ValueError("Architect output missing")
                    schema_prompt = (prompts_dir / "schema_agent.md").read_text(encoding="utf-8")
                    schema_model = self._stage_model("schema")
                    if self._settings.smart_enable_stage_cache:
                        schema_key = stage_cache.make_key(
                            "schema",
                            {
                                "architect_output": state.architect_output.model_dump(mode="json"),
                                "template": schema_prompt,
                                "model": schema_model,
                            },
                        )
                        cached = stage_cache.get("schema", schema_key)
                        if cached is not None:
                            state.schema_output = SchemaOutput.model_validate(cached)
                            self._persist_schema_artifacts(store, state.schema_output)
                        else:
                            state.schema_output = schema.run(state.architect_output, model_override=schema_model)
                            stage_cache.set("schema", schema_key, state.schema_output.model_dump())
                    else:
                        state.schema_output = schema.run(state.architect_output, model_override=schema_model)
                elif node == "api":
                    if state.architect_output is None or state.schema_output is None:
                        raise ValueError("Architecture or schema output missing")
                    retrieval_output = state.retrieval_output or retriever.retrieve(state.user_prompt)
                    state.api_output = api_agent.run(
                        state.architect_output,
                        state.schema_output,
                        retrieval_output,
                        model_override=self._stage_model("api"),
                    )
                elif node == "frontend":
                    if state.planner_output is None or state.api_output is None:
                        raise ValueError("Planner or API output missing")
                    retrieval_output = state.retrieval_output or retriever.retrieve(state.user_prompt)
                    state.frontend_output = frontend_agent.run(
                        state.planner_output,
                        state.api_output,
                        retrieval_output,
                        model_override=self._stage_model("frontend"),
                    )
                elif node == "codegen":
                    if state.api_output is None or state.frontend_output is None:
                        raise ValueError("API or frontend output missing")
                    state.codegen_output = codegen_agent.run(state.api_output, state.frontend_output)
                elif node == "validation":
                    summary = self._run_validations(state, schema_validator, api_checker, ui_mapper)
                    state.validation_summary = summary
                    validation_path = store.write_json_artifact("validation_results.json", summary.model_dump())
                    store.append_manifest(validation_path)
                elif node == "reviewer":
                    if self._should_run_reviewer(state):
                        state.review_output = reviewer.run(state, model_override=self._stage_model("reviewer"))
                    else:
                        state.review_output = self._persist_skipped_review(store)
                elif node == "correction":
                    self._apply_correction_loop(
                        state=state,
                        store=store,
                        retriever=retriever,
                        schema=schema,
                        api_agent=api_agent,
                        frontend_agent=frontend_agent,
                        codegen_agent=codegen_agent,
                        reviewer=reviewer,
                        schema_validator=schema_validator,
                        api_checker=api_checker,
                        ui_mapper=ui_mapper,
                    )
                elif node == "package_artifacts":
                    manifest_data = store.read_manifest()
                    state.artifact_manifest = ArtifactManifest(files=manifest_data.get("files", []))
                    package_output = packager.package(state)
                    state.package_summary = package_output["summary"]

                state.completed_steps.append(node)

            state.status = "completed"
        except Exception as exc:  # noqa: BLE001
            state.status = "failed"
            state.errors.append(str(exc))
            state.errors.append(traceback.format_exc())

        state.llm_backend = llm_client.backend
        state.llm_fallback_reason = llm_client.fallback_reason

        run_state_path = store.write_json_artifact("run_state.json", state.model_dump(mode="json"))
        store.append_manifest(run_state_path)
        manifest_data = store.read_manifest()
        state.artifact_manifest = ArtifactManifest(files=manifest_data.get("files", []))

        store.write_json_artifact("run_state.json", state.model_dump(mode="json"))
        return state

    def get_run(self, run_id: str) -> RunState | None:
        state_path = self._settings.runs_path / run_id / "run_state.json"
        if not state_path.exists():
            return None
        payload = state_path.read_text(encoding="utf-8")
        return RunState.model_validate_json(payload)

    def _apply_correction_loop(
        self,
        state: RunState,
        store: ArtifactStore,
        retriever: LocalTemplateRetriever,
        schema: SchemaAgent,
        api_agent: APIAgent,
        frontend_agent: FrontendAgent,
        codegen_agent: CodegenAgent,
        reviewer: ReviewerAgent,
        schema_validator: SchemaValidator,
        api_checker: APIChecker,
        ui_mapper: FrontendBackendMapper,
    ) -> None:
        review = state.review_output
        if review is None:
            return

        critical_issues = [issue for issue in review.issues if issue.severity == "critical"]
        if not critical_issues or state.correction_count >= 1:
            return

        state.correction_count += 1
        feedback = [f"{issue.code}: {issue.suggested_fix}" for issue in critical_issues]
        targets = {issue.target_stage for issue in critical_issues}

        if "schema" in targets and state.architect_output is not None:
            state.schema_output = schema.run(state.architect_output, model_override=self._stage_model("schema"))

        needs_api = any(target in targets for target in {"schema", "api"})
        needs_frontend = any(target in targets for target in {"schema", "api", "frontend"})
        needs_codegen = any(target in targets for target in {"schema", "api", "frontend", "codegen", "validation"})

        retrieval_output = state.retrieval_output or retriever.retrieve(state.user_prompt)

        if needs_api and state.architect_output is not None and state.schema_output is not None:
            state.api_output = api_agent.run(
                state.architect_output,
                state.schema_output,
                retrieval_output,
                reviewer_feedback=feedback,
                artifact_prefix="04_api_corrected",
                model_override=self._stage_model("api"),
            )

        if needs_frontend and state.planner_output is not None and state.api_output is not None:
            state.frontend_output = frontend_agent.run(
                state.planner_output,
                state.api_output,
                retrieval_output,
                reviewer_feedback=feedback,
                artifact_prefix="05_frontend_corrected",
                model_override=self._stage_model("frontend"),
            )

        if needs_codegen and state.api_output is not None and state.frontend_output is not None:
            state.codegen_output = codegen_agent.run(
                state.api_output,
                state.frontend_output,
                artifact_prefix="06_codegen_corrected",
            )

        summary = self._run_validations(state, schema_validator, api_checker, ui_mapper)
        state.validation_summary = summary
        validation_path = store.write_json_artifact("validation_results_corrected.json", summary.model_dump())
        store.append_manifest(validation_path)

        if self._should_run_reviewer(state):
            state.review_output = reviewer.run(
                state,
                filename="07_review_corrected.json",
                model_override=self._stage_model("reviewer"),
            )
        else:
            state.review_output = self._persist_skipped_review(store, filename="07_review_corrected.json")

    def _run_validations(
        self,
        state: RunState,
        schema_validator: SchemaValidator,
        api_checker: APIChecker,
        ui_mapper: FrontendBackendMapper,
    ) -> ValidationSummary:
        warnings = []
        errors = []
        checks_run: list[str] = []

        if state.architect_output is not None:
            schema_warnings, schema_errors = schema_validator.validate(state.architect_output)
            warnings.extend(schema_warnings)
            errors.extend(schema_errors)
            checks_run.append("schema_validator")

        if state.api_output is not None and state.architect_output is not None:
            api_warnings, api_errors = api_checker.check(state.api_output, state.architect_output)
            warnings.extend(api_warnings)
            errors.extend(api_errors)
            checks_run.append("api_checker")

        if state.frontend_output is not None and state.api_output is not None:
            ui_warnings, ui_errors = ui_mapper.validate_mapping(state.frontend_output, state.api_output)
            warnings.extend(ui_warnings)
            errors.extend(ui_errors)
            checks_run.append("frontend_backend_mapper")

        return ValidationSummary(
            passed=len(errors) == 0,
            checks_run=checks_run,
            warnings=warnings,
            errors=errors,
        )

    def _stage_model(self, stage: str) -> str:
        model = getattr(self._settings, f"gemini_model_{stage}", None)
        return model or self._settings.gemini_model

    def _should_run_reviewer(self, state: RunState) -> bool:
        if self._settings.smart_reviewer_on_clean:
            return True
        if state.validation_summary is None:
            return True
        return bool(state.validation_summary.errors or state.validation_summary.warnings)

    def _persist_planner_artifacts(self, store: ArtifactStore, output: PlannerOutput) -> None:
        json_path = store.write_json_artifact("01_planner.json", output.model_dump())
        md_path = store.write_text_artifact("requirements.md", _to_requirements_markdown(output))
        store.append_manifest(json_path)
        store.append_manifest(md_path)

    def _persist_architect_artifacts(self, store: ArtifactStore, output: ArchitectOutput) -> None:
        json_path = store.write_json_artifact("02_architect.json", output.model_dump())
        md_path = store.write_text_artifact("architecture.md", _to_architecture_markdown(output))
        store.append_manifest(json_path)
        store.append_manifest(md_path)

    def _persist_schema_artifacts(self, store: ArtifactStore, output: SchemaOutput) -> None:
        json_path = store.write_json_artifact("03_schema.json", output.model_dump())
        sql_path = store.write_text_artifact("schema.sql", output.sql)
        store.append_manifest(json_path)
        store.append_manifest(sql_path)

    def _persist_skipped_review(self, store: ArtifactStore, filename: str = "07_review.json") -> ReviewOutput:
        output = ReviewOutput(
            issues=[],
            corrected_summary="Reviewer skipped by smart policy: validation was clean and no warnings.",
            correction_needed=False,
        )
        path = store.write_json_artifact(filename, output.model_dump())
        store.append_manifest(path)
        return output
