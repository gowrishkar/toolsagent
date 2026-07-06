"""Search as Code — programmable retrieval, validation, filtering, and ranking."""

from .pipeline import run_pipeline
from .profile import load_profile

__all__ = ["run_pipeline", "load_profile"]
__version__ = "1.0.0"