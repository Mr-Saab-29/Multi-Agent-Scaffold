from app.models.api_models import APIOutput, EndpointSpec, RouteGroupSpec
from app.models.architect_models import ArchitectOutput
from app.models.shared import EntitySpec, FieldSpec, RelationshipSpec
from app.models.frontend_models import FrontendOutput, ScreenAPIMap
from app.tools.api_checker import APIChecker
from app.tools.schema_validator import SchemaValidator
from app.tools.ui_mapper import FrontendBackendMapper


def test_schema_validator_flags_missing_pk_and_unknown_rel() -> None:
    architect = ArchitectOutput(
        architecture_style="modular",
        components=[],
        data_entities=[
            EntitySpec(name="orders", fields=[FieldSpec(name="amount", type="int")]),
        ],
        relationships=[
            RelationshipSpec(from_entity="orders", to_entity="users", relation_type="one_to_many"),
        ],
        sequence_overview=[],
    )

    warnings, errors = SchemaValidator().validate(architect)
    assert not warnings
    codes = {e.code for e in errors}
    assert "SCHEMA_MISSING_PK" in codes
    assert "SCHEMA_UNKNOWN_RELATION_ENTITY" in codes


def test_api_checker_flags_duplicates() -> None:
    api = APIOutput(
        route_groups=[
            RouteGroupSpec(
                name="users",
                base_path="/api/users",
                endpoints=[
                    EndpointSpec(method="GET", path="/api/users", summary="List users"),
                    EndpointSpec(method="GET", path="/api/users", summary="Duplicate list users"),
                ],
            )
        ],
        request_models=[],
        response_models=[],
        auth_requirements=[],
        validation_notes=[],
    )
    architect = ArchitectOutput(
        architecture_style="modular",
        components=[],
        data_entities=[
            EntitySpec(name="users", fields=[FieldSpec(name="id", type="uuid")]),
        ],
        relationships=[],
        sequence_overview=[],
    )

    warnings, errors = APIChecker().check(api, architect)
    assert warnings
    assert any(e.code == "API_DUPLICATE_PATH" for e in errors)


def test_ui_mapper_flags_unknown_endpoint() -> None:
    api = APIOutput(
        route_groups=[
            RouteGroupSpec(
                name="users",
                base_path="/api/users",
                endpoints=[EndpointSpec(method="GET", path="/api/users", summary="List users")],
            )
        ],
        request_models=[],
        response_models=[],
        auth_requirements=[],
        validation_notes=[],
    )
    frontend = FrontendOutput(
        screens=[],
        components=[],
        user_flows=[],
        screen_api_mapping=[ScreenAPIMap(screen="Users", endpoints=["GET /api/unknown"])],
    )

    warnings, errors = FrontendBackendMapper().validate_mapping(frontend, api)
    assert not warnings
    assert any(e.code == "UI_UNKNOWN_ENDPOINT" for e in errors)
