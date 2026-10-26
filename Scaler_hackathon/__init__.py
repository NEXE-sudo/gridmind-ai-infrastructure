"""Scaler Hackathon environment public API.

Legacy OpenEnv-backed symbols are loaded on demand, keeping unrelated tools
and GridMind tests importable without eagerly loading the legacy runtime.
"""

__all__ = [
    "EnergyGridAction",
    "EnergyGridEnv",
    "EnergyGridObservation",
    "ScalerHackathonAction",
    "ScalerHackathonObservation",
]


def __getattr__(name: str):
    if name == "EnergyGridEnv":
        from .client import EnergyGridEnv

        return EnergyGridEnv
    if name in {
        "EnergyGridAction",
        "EnergyGridObservation",
        "ScalerHackathonAction",
        "ScalerHackathonObservation",
    }:
        from .models import EnergyGridAction, EnergyGridObservation

        exports = {
            "EnergyGridAction": EnergyGridAction,
            "EnergyGridObservation": EnergyGridObservation,
            "ScalerHackathonAction": EnergyGridAction,
            "ScalerHackathonObservation": EnergyGridObservation,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
