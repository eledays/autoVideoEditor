"""Тонкая обёртка для совместимости: экспортируем run_pipeline из app.orchestrator."""

from src.app.orchestrator import run_pipeline  # re-export

__all__ = ["run_pipeline"]
