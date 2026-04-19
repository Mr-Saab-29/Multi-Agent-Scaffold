from app.models.api_models import APIOutput
from app.models.architect_models import ArchitectOutput
from app.models.validation_models import ValidationIssue


class APIChecker:
    def check(self, api_output: APIOutput, architect_output: ArchitectOutput) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
        warnings: list[ValidationIssue] = []
        errors: list[ValidationIssue] = []

        seen_paths: set[tuple[str, str]] = set()
        for group in api_output.route_groups:
            for endpoint in group.endpoints:
                signature = (endpoint.method.upper(), endpoint.path)
                if signature in seen_paths:
                    errors.append(
                        ValidationIssue(
                            code="API_DUPLICATE_PATH",
                            message=f"Duplicate endpoint detected: {endpoint.method.upper()} {endpoint.path}",
                        )
                    )
                seen_paths.add(signature)

        methods_by_entity: dict[str, set[str]] = {}
        for group in api_output.route_groups:
            group_name = group.name.lower()
            methods = {e.method.upper() for e in group.endpoints}
            methods_by_entity[group_name] = methods

        for entity in architect_output.data_entities:
            key = entity.name.lower()
            methods = methods_by_entity.get(key, set())
            if not methods:
                warnings.append(
                    ValidationIssue(
                        code="API_ENTITY_NO_GROUP",
                        message=f"No route group found for entity '{entity.name}'",
                    )
                )
                continue
            missing = {"POST", "GET", "PATCH", "DELETE"} - methods
            if missing:
                warnings.append(
                    ValidationIssue(
                        code="API_PARTIAL_CRUD",
                        message=f"Entity '{entity.name}' missing methods: {', '.join(sorted(missing))}",
                    )
                )

        return warnings, errors
