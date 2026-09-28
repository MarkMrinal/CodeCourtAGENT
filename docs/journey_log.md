# CodeCourt Journey Log

### Phase 0: Setup & Architecture
- Configured Groq API client with `llama-3.3-70b-versatile` model.
- Planted vulnerable sample modules (`sample_project/auth.py`, `billing.py`).
- Isolated LLM usage strictly to debate and phrasing layers; static analysis remains 100% deterministic.

### Phase 1: HEUSC Inspector
- Implemented AST code auditor and Radon cyclomatic complexity analyzer.
- Added shallow git clone capability for public repositories.
- Normalized findings schema with unique citation IDs (`F1`, `F2`, ...).

### Phase 2: The Court & Citation Validator
- Implemented Viktor (Perfectionist) vs Viego (Pragmatist) adversarial debate loop.
- Added Presiding Judge multi-round adjudication.
- Integrated citation validator checking all claims against verified findings.

### Phase 3: Streamlit Interface & State Handoff
- Created unified interface with Inspector, Court, and Guided Fix demo tabs.
- Frictionless state handoff with zero copy-pasting.

### Phase 3.5: Guided Fix Demo
- End-to-end SQL injection patch application, pytest execution, and diff visualization.
