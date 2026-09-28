"""
Shared state management for CodeCourt.
Bridges Inspector findings, Court debates, and UI state.
"""
from typing import Dict, Any, List, Optional


def create_initial_state() -> Dict[str, Any]:
    """Returns a fresh session state structure."""
    return {
        "project_path": None,
        "is_github_repo": False,
        "findings": [],      # List of finding dicts from HEUSC
        "verdict": None,     # Dict produced by Judge
        "debate_transcript": [], # List of round dialogue dicts: {"speaker": ..., "text": ..., "citations": [...], "valid_citations": [...], "invalid_citations": [...]}
        "history": [],       # Chat history
    }


def add_finding(state: Dict[str, Any], finding: Dict[str, Any]) -> None:
    """Add a single finding to state."""
    state.setdefault("findings", []).append(finding)


def set_findings(state: Dict[str, Any], findings: List[Dict[str, Any]]) -> None:
    """Overwrites current findings list in state."""
    state["findings"] = findings


def clear_state(state: Dict[str, Any]) -> None:
    """Resets state to initial blank session."""
    initial = create_initial_state()
    state.clear()
    state.update(initial)
