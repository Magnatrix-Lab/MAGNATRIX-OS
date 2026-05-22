"""
MAGNATRIX Python SDK
pip install magnatrix-sdk

Unified client untuk MAGNATRIX Agentic OS.
"""
from .client import MAGNATRIXClient
from .agent import Agent
from .pipeline import Pipeline
from .skill import Skill
from .mesh import MeshClient

__version__ = "0.1.0"
__all__ = ["MAGNATRIXClient", "Agent", "Pipeline", "Skill", "MeshClient"]
