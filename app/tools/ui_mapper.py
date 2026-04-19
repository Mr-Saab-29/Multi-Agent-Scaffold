from app.models.api_models import APIOutput
from app.models.frontend_models import FrontendOutput
from app.models.validation_models import ValidationIssue


class FrontendBackendMapper:
    def validate_mapping(self, frontend_output: FrontendOutput, api_output: APIOutput) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
        warnings: list[ValidationIssue] = []
        errors: list[ValidationIssue] = []

        known_endpoints = {
            f"{ep.method.upper()} {ep.path}"
            for group in api_output.route_groups
            for ep in group.endpoints
        }

        for mapping in frontend_output.screen_api_mapping:
            if not mapping.endpoints:
                warnings.append(
                    ValidationIssue(
                        code="UI_SCREEN_NO_ENDPOINTS",
                        message=f"Screen '{mapping.screen}' has no mapped endpoints",
                    )
                )
            for endpoint in mapping.endpoints:
                if endpoint not in known_endpoints:
                    errors.append(
                        ValidationIssue(
                            code="UI_UNKNOWN_ENDPOINT",
                            message=f"Screen '{mapping.screen}' references unknown endpoint '{endpoint}'",
                        )
                    )

        return warnings, errors
