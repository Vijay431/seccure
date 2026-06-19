"""Fixer routing for supported and unsupported dependency ecosystems."""

from __future__ import annotations

from dataclasses import dataclass

from agent.config import DependencyFinding

_NODE_ECOSYSTEMS = {"npm", "yarn", "pnpm", "javascript", "node"}
_PYTHON_ECOSYSTEMS = {"pip", "pipenv", "poetry", "uv", "python"}


@dataclass(frozen=True)
class FixerRoute:
    ecosystem: str
    supported: bool
    family: str | None = None
    conflict_reason: str | None = None


def route_finding(finding: DependencyFinding) -> FixerRoute:
    """Route a dependency finding to the v1 fixer family."""

    ecosystem = finding.ecosystem.lower()
    if ecosystem in _NODE_ECOSYSTEMS:
        return FixerRoute(ecosystem=ecosystem, supported=True, family="node")
    if ecosystem in _PYTHON_ECOSYSTEMS:
        return FixerRoute(ecosystem=ecosystem, supported=True, family="python")
    return FixerRoute(
        ecosystem=ecosystem,
        supported=False,
        conflict_reason=f"unsupported ecosystem fixer: {ecosystem}",
    )
