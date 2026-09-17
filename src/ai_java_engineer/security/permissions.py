"""Tool permission boundaries and RBAC policy evaluation."""

from enum import Enum

from ai_java_engineer.infrastructure.errors import SecurityViolationError


class RiskLevel(str, Enum):
    LOW = "LOW"            # read_file, search_code (autonomous)
    MEDIUM = "MEDIUM"      # write_file, apply_patch (tracked in diff)
    HIGH = "HIGH"          # git_push, create_pr (human approval required)
    FORBIDDEN = "FORBIDDEN"# direct merge, arbitrary bash, production deploy


TOOL_PERMISSIONS: dict[str, RiskLevel] = {
    "read_file": RiskLevel.LOW,
    "search_code": RiskLevel.LOW,
    "repository_map": RiskLevel.LOW,
    "write_file": RiskLevel.MEDIUM,
    "apply_patch": RiskLevel.MEDIUM,
    "run_build": RiskLevel.MEDIUM,
    "run_tests": RiskLevel.MEDIUM,
    "git_commit": RiskLevel.MEDIUM,
    "git_push": RiskLevel.HIGH,
    "create_pr": RiskLevel.HIGH,
    "merge_to_main": RiskLevel.FORBIDDEN,
    "execute_arbitrary_shell": RiskLevel.FORBIDDEN,
}


def check_tool_permission(tool_name: str, human_approved: bool = False) -> None:
    """Evaluates whether a tool may be executed given current governance context."""
    risk = TOOL_PERMISSIONS.get(tool_name, RiskLevel.FORBIDDEN)

    if risk == RiskLevel.FORBIDDEN:
        raise SecurityViolationError(f"Tool '{tool_name}' is strictly forbidden by governance policy.")

    if risk == RiskLevel.HIGH and not human_approved:
        raise SecurityViolationError(
            f"Tool '{tool_name}' is high-risk and requires explicit human approval."
        )
