from app.models.architect_models import ArchitectOutput
from app.models.validation_models import ValidationIssue


class SchemaValidator:
    def validate(self, architect_output: ArchitectOutput) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
        warnings: list[ValidationIssue] = []
        errors: list[ValidationIssue] = []

        entity_names = {entity.name for entity in architect_output.data_entities}
        for entity in architect_output.data_entities:
            has_primary = any(field.name == "id" for field in entity.fields)
            if not has_primary:
                errors.append(
                    ValidationIssue(
                        code="SCHEMA_MISSING_PK",
                        message=f"Entity '{entity.name}' has no 'id' primary key field",
                    )
                )

        for rel in architect_output.relationships:
            if rel.from_entity not in entity_names or rel.to_entity not in entity_names:
                errors.append(
                    ValidationIssue(
                        code="SCHEMA_UNKNOWN_RELATION_ENTITY",
                        message=f"Relationship '{rel.from_entity}->{rel.to_entity}' refers to unknown entity",
                    )
                )

        if not architect_output.relationships:
            warnings.append(
                ValidationIssue(
                    code="SCHEMA_NO_RELATIONSHIPS",
                    message="No entity relationships were defined",
                )
            )

        return warnings, errors
