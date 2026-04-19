from app.models.api_models import APIOutput
from app.models.codegen_models import CodegenOutput, GeneratedFileSpec
from app.models.frontend_models import FrontendOutput
from app.services.artifact_store import ArtifactStore
from app.tools.file_builder import FileTreeBuilder


class CodegenAgent:
    def __init__(self, artifact_store: ArtifactStore):
        self._store = artifact_store
        self._file_builder = FileTreeBuilder(artifact_store.base_dir)

    def run(
        self,
        api_output: APIOutput,
        frontend_output: FrontendOutput,
        artifact_prefix: str = "06_codegen",
    ) -> CodegenOutput:
        generated_root = self._file_builder.ensure_generated_tree()

        backend_files: list[GeneratedFileSpec] = []
        for group in api_output.route_groups:
            route_path = generated_root / "backend" / "routes" / f"{group.name}_routes.py"
            model_path = generated_root / "backend" / "models" / f"{group.name}_models.py"
            route_content = _render_route_stub(group.name, group.base_path)
            model_content = _render_model_stub(group.name)
            written_route = self._store.write_text_artifact(str(route_path.relative_to(self._store.base_dir)), route_content)
            written_model = self._store.write_text_artifact(str(model_path.relative_to(self._store.base_dir)), model_content)
            self._store.append_manifest(written_route)
            self._store.append_manifest(written_model)
            backend_files.extend(
                [
                    GeneratedFileSpec(path=written_route, language="python", description=f"Route stubs for {group.name}"),
                    GeneratedFileSpec(path=written_model, language="python", description=f"Model stubs for {group.name}"),
                ]
            )

        frontend_files: list[GeneratedFileSpec] = []
        for screen in frontend_output.screens:
            safe_name = screen.name.lower()
            page_path = generated_root / "frontend" / "pages" / f"{safe_name}.tsx"
            page_content = _render_page_stub(screen.name)
            written_page = self._store.write_text_artifact(str(page_path.relative_to(self._store.base_dir)), page_content)
            self._store.append_manifest(written_page)
            frontend_files.append(
                GeneratedFileSpec(path=written_page, language="typescript", description=f"Page stub for {screen.name}")
            )

        for component in frontend_output.components:
            safe_name = component.name.lower()
            component_path = generated_root / "frontend" / "components" / f"{safe_name}.tsx"
            component_content = _render_component_stub(component.name, component.purpose)
            written_component = self._store.write_text_artifact(
                str(component_path.relative_to(self._store.base_dir)),
                component_content,
            )
            self._store.append_manifest(written_component)
            frontend_files.append(
                GeneratedFileSpec(
                    path=written_component,
                    language="typescript",
                    description=f"Component stub for {component.name}",
                )
            )

        output = CodegenOutput(
            generated_root=str(generated_root),
            backend_files=backend_files,
            frontend_files=frontend_files,
            notes=["Stubs are minimal and meant for manual extension", "No runtime framework wiring yet"],
        )

        json_path = self._store.write_json_artifact(f"{artifact_prefix}.json", output.model_dump())
        self._store.append_manifest(json_path)
        return output


def _render_route_stub(group_name: str, base_path: str) -> str:
    return (
        "from fastapi import APIRouter\n\n"
        f"router = APIRouter(prefix=\"{base_path}\", tags=[\"{group_name}\"])\n\n"
        "@router.get(\"\")\n"
        "def list_items() -> dict[str, str]:\n"
        f"    return {{\"message\": \"List {group_name}\"}}\n"
    )


def _render_model_stub(group_name: str) -> str:
    class_name = "".join(part.capitalize() for part in group_name.split("_"))
    if class_name.endswith("s"):
        class_name = class_name[:-1]
    return (
        "from pydantic import BaseModel\n\n"
        f"class {class_name}Base(BaseModel):\n"
        "    id: str\n"
        "    # add additional fields\n"
    )


def _render_page_stub(screen_name: str) -> str:
    return (
        "export default function Page() {\n"
        f"  return <main>{screen_name} page stub</main>;\n"
        "}\n"
    )


def _render_component_stub(component_name: str, purpose: str) -> str:
    return (
        f"export function {component_name}() {{\n"
        f"  return <div>{component_name}: {purpose}</div>;\n"
        "}\n"
    )
