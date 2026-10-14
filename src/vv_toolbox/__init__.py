"""Synthetic vessels, millimeter units, no patient-derived data."""
from .model import VesselGraph, generate
from .generator import ARCH_VARIANTS, COMMUNICATORS

__all__ = ["VesselGraph", "generate", "ARCH_VARIANTS", "COMMUNICATORS"]
