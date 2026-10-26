"""Scaler Hackathon environment server components.

Keep the legacy environment import lazy so the independent GridMind API does
not need to load OpenEnv just to import ``server.gridmind_app``.
"""

__all__ = ["EnergyGridEnvironment"]


def __getattr__(name: str):
    if name == "EnergyGridEnvironment":
        from .energy_grid_environment import EnergyGridEnvironment

        return EnergyGridEnvironment
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
