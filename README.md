# CodeCourt

**Evidence-grounded, multi-agent code review.** A code Inspector gathers measurable facts about a codebase. A Court of two opposing AI reviewers debates what to do about them, citing evidence for every claim. A Judge hands down a verdict. One guided demo shows the verdict actually applied as a fix.

> Course project — built in phases, presented as a working demo, extended after presentation.

---

## 1. Why this exists

AI code reviewers usually hand you an opinion with nothing behind it. CodeCourt separates **evidence** from **judgment**:

- The **Inspector (HEUSC)** measures the code — function length, complexity, duplication, missing tests — and gives every finding an ID. No AI, no opinions, just facts.
- The **Court (Viktor vs. Viego)** debates those facts. Every argument must cite a finding ID. A validator flags any citation that doesn't exist, so the agents can't invent problems.
- The **Judge** turns the debate into a prioritized verdict: fix now, fix later.
- One **guided demo** shows what happens when a verdict is actually carried out: a real patch, applied and tested, on one pre-chosen example.

Both agent systems work **independently** (Inspector alone, Court alone) or **together**, handed off through one shared interface with no manual copy-pasting.

---

## 2. Meet the agents

### HEUSC — The Inspector
*Named for the AI butler in* The Millionaire Detective – Balance: Unlimited.

**Role:** gathers evidence. Never argues, never opines — reports.
**Personality:** the calm, hyper-competent aide who treats every scan like it's already handled before you finished asking. Formal, unhurried, precise. Refers to findings like case files. Nothing rattles it; it simply has the answer ready.

> *"Scan complete. Seven matters warrant your attention, three of them urgent. Shall I prepare the full report, or would you prefer I begin with what's most likely to cause you trouble first?"*

**On chatting:** HEUSC's *findings* are always rule-based — no AI touches the evidence itself. But when you talk to it directly ("hello", "explain this more simply"), a thin conversational layer (one LLM call, `core/heusc_voice.py`) rephrases the existing findings in HEUSC's voice. It's only allowed to reword what's already in `findings.json` — never to add a new claim. This keeps "the evidence never lies" true even though the *delivery* is conversational.

**On public repos:** point it at a GitHub URL and it works the same way. `git clone --depth 1` pulls the repo into a temp folder first, then the same rule-based scan runs on it. No GitHub API key needed — just `git` installed locally.

### VIKTOR — The Perfectionist
*Tone inspired by Arcane's Viktor* — original dialogue, not quoted from the show.

**Role:** argues for correctness, no matter the cost.
**Personality:** measured, clinical, almost philosophical about progress. Sees every unresolved flaw as decay waiting to compound. Doesn't raise his voice — doesn't need to. Believes shortcuts are how systems quietly die.

> *"An inefficiency tolerated today is a failure scheduled for tomorrow. I am not proposing perfection as an ideal. I am proposing it as the only acceptable outcome."*

### VIEGO — The Pragmatist
*Tone inspired by League of Legends' Viego* — original dialogue, not quoted from the game.

**Role:** argues for shipping, for momentum, for what's actually achievable before time runs out.
**Personality:** intense, blunt, a little mournful about time wasted on things that don't matter. Impatient with hesitation. Not careless — just convinced that waiting for perfect is its own kind of failure.

> *"You'll polish this until it's flawless and the deadline will bury us both. I've watched 'later' become 'never' more times than I care to count. Fix what matters. Ship the rest."*

### The Verdict — Judge (unnamed)
Reads the exchange, weighs both sides, and outputs a prioritized list: fix now / fix later, with reasons. No persona assigned yet — give it a name if you want one, or leave it neutral as the system's "ruling."

---

## 3. Architecture

```
                     ┌──────────────────────┐
   your code  ──────▶│   HEUSC (Inspector)   │──────▶ findings.json
                     └──────────────────────┘              │
                                                              │  (shared state)
                     ┌──────────────────────┐              │
    pasted code ────▶│  VIKTOR ⚔ VIEGO       │◀─────────────┘
   or @court call     │   (the Court)         │──────▶ verdict.json
                     └──────────────────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │   Guided Fix Demo     │──────▶ patched file + test result
                     │  (one known snippet)  │
                     └──────────────────────┘
```

**The bridge is a single shared session dict**, not a framework:

```python
state = {
    "project_path": None,
    "findings": [],     # written by HEUSC
    "verdict": None,     # written by the Court
    "history": [],       # chat log
}
```

Either agent can be called on its own. If the Court is called after HEUSC has already run, it reads `state["findings"]` automatically — no manual handoff needed. Routing is explicit (`@heusc`, `@court` commands or buttons), not AI-guessed, so it's reliable live.

---

## 4. Project structure

```
codecourt/
├── README.md
├── requirements.txt
├── .env                      # GROQ_API_KEY=... (never commit this)
├── .gitignore
│
├── core/
│   ├── llm.py                 # single ask(prompt, persona) wrapper — swap models here
│   ├── inspector.py            # HEUSC: scans a path or GitHub URL, returns findings list (no AI)
│   ├── heusc_voice.py            # thin LLM layer: rephrases existing findings conversationally, adds no new claims
│   ├── court.py                 # Viktor + Viego + Judge debate loop
│   └── state.py                 # shared session dict helpers
│
├── demo/
│   ├── snippet.py               # the one pre-chosen buggy function (SQL injection example)
│   ├── snippet_test.py          # test proving the vulnerability / proving the fix
│   └── fallback_patch.py        # known-good patch, used only if live fix fails
│
├── sample_project/            # small Python project with a few real issues, for the live repo scan
│   ├── ...
│   └── tests/
│
├── app.py                       # Streamlit interface — chat, mode picker, buttons
│
└── docs/
    ├── journey_log.md          # screenshots + notes as you build — becomes your slides/assignment
    └── findings_schema.md      # the fixed format both systems agree on
```

---

## 5. `findings.json` — the shared language

Every finding HEUSC produces, and every citation the Court makes, uses this shape:

```json
{
  "id": "F1",
  "file": "app/auth.py",
  "function": "login_user",
  "issue": "duplicate_code",
  "detail": "Identical block also found in app/register.py and app/reset.py",
  "metric": null,
  "severity": "medium"
}
```

```json
{
  "id": "F2",
  "file": "app/auth.py",
  "function": "run_query",
  "issue": "sql_injection_risk",
  "detail": "Query built via string concatenation with user input",
  "metric": null,
  "severity": "high"
}
```

The Court must cite `id` values in its arguments. A validator checks every cited ID against this file and flags anything that doesn't exist.

---

## 6. Roadmap — Phase 0 to 3.5 (tonight's scope)

| Phase | Deliverable | Files touched | Done when... |
|---|---|---|---|
| **0 — Setup** (~30m) | venv, deps installed, one test API call works, `sample_project/` with a few planted issues + real tests | `.env`, `requirements.txt`, `sample_project/` | `python -c "from core.llm import ask; print(ask('hi'))"` returns text |
| **1 — HEUSC** (~1h) | `inspector.py` scans a local folder *or* a public GitHub URL (`git clone --depth 1` first), outputs `findings.json` | `core/inspector.py`, `docs/findings_schema.md` | Running it on `sample_project/` and on one real GitHub URL both produce correct, sensible findings |
| **2 — The Court** (~1h) | `court.py`: Viktor + Viego, 2 rounds, Judge verdict, citation validator | `core/court.py` | Feeding it findings produces a transcript with real disagreement and a validator that catches a fake ID |
| **3 — Interface** (~1h, +15–20m if voice layer included) | Streamlit app: mode picker (HEUSC only / Court only / Both), shared `state`, `@heusc` / `@court` commands or buttons, optional `heusc_voice.py` for greetings/plain-language explanations | `app.py`, `core/state.py`, `core/heusc_voice.py` | You can start in HEUSC, then call the Court mid-chat and it picks up findings automatically, with no copy-paste |
| **3.5 — Guided Fix Demo** (~45m) | One button: real scan → real debate on the SQL-injection snippet → Judge's verdict applied as an actual patch → test run → before/after diff shown | `demo/snippet.py`, `demo/snippet_test.py`, `demo/fallback_patch.py` | Clicking the button produces a passing test and a visible diff, end to end |

**Stop line for tonight: end of Phase 3.5.** That's a complete, demoable, honestly-scoped project.

**Held for later (do not start tonight):**
- Phase 4 — hardening (stale-scan detection, saved state, polish), slides, written assignment
- Phase 5 — general fix-and-verify loop (any code, not just the one snippet)
- Phase 6 — evaluation (scanner-only vs. single-agent vs. Court, on a benchmark set)
- Phase 7 — MCP wrappers, more languages, a properly-defined health score

If Phase 3 runs long: drop the chat-command parsing and use plain buttons instead ("Run HEUSC", "Send to Court") — the shared-state handoff still works exactly the same way.

---

## 7. Setup

```bash
git clone <your-repo-url> codecourt
cd codecourt
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add your GROQ_API_KEY
streamlit run app.py
```

`requirements.txt` (starting point):
```
streamlit
groq
python-dotenv
radon
pytest
```

> We use Groq's Python SDK with high-speed models (such as `llama-3.3-70b-versatile`):
> ```python
> from groq import Groq
> client = Groq()  # reads GROQ_API_KEY from the environment automatically
> response = client.chat.completions.create(
>     model="llama-3.3-70b-versatile",
>     messages=[{"role": "user", "content": "hello"}]
> )
> print(response.choices[0].message.content)
> ```
> Get your free key at [console.groq.com](https://console.groq.com/keys).

---

## 8. Handover notes (VS Code / Antigravity / anyone picking this up)

- **Everything routes through `core/llm.py`.** If you switch providers or models, change it in exactly one place.
- **`findings.json` is the contract.** If HEUSC's output format changes, `court.py`'s citation validator breaks — update both together.
- **Guided Fix Demo is intentionally hardcoded to one snippet.** It is *not* the general fix loop (that's Phase 5, held). Don't present it as working on arbitrary code — say plainly it's a controlled walkthrough.
- **`docs/journey_log.md`** — add a line and a screenshot every time something breaks or works for the first time. This is the raw material for slides and the written assignment; don't reconstruct it from memory later.
- **Free-tier API limits are per-project, not per-key**, and vary by model — check your actual dashboard rather than trusting a fixed number. Cache/save debate transcripts to disk so replaying the demo doesn't burn quota.

---

## 9. Status

- [x] Phase 0 — Setup
- [x] Phase 1 — HEUSC (Inspector)
- [x] Phase 2 — The Court (Viktor + Viego + Judge)
- [x] Phase 3 — Interface + handoff
- [x] Phase 3.5 — Guided Fix Demo
- [ ] Phase 4+ — held for post-presentation extension
