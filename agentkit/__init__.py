"""
AgentKit utilities for the HHMap project.

The package currently exposes connector implementations that map the tool IDs
defined in `agentkit/builder/happy_hour_agents.yaml` to concrete callables.
"""

from .connectors import connectors  # re-export for convenience

__all__ = ["connectors"]
