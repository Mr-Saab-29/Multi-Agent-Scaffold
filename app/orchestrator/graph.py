from collections.abc import Sequence


def day1_graph() -> Sequence[str]:
    """Static execution order for Day 1."""
    return ("planner", "architect", "schema")


def day2_graph() -> Sequence[str]:
    """Static execution order for Day 2."""
    return (
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
    )
