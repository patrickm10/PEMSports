"""
Project-wide constants.

This module exists so backend and pipeline code can share a single source of truth
without importing deep pipeline modules from runtime-sensitive areas.
"""

from pipelines.constants import TEAM_MAP  # re-export (single source of truth)

__all__ = ["TEAM_MAP"]

