"""
The Court — Multi-agent adversarial debate and verifiable adjudication.
- VIKTOR: The Perfectionist (Arcane-inspired: correctness, technical debt elimination)
- VIEGO: The Pragmatist (LoL-inspired: ship value now, resist gold-plating)
- JUDGE: Impartial arbiter rendering prioritized verdict (Fix Now / Fix Later)
- CITATION VALIDATOR: Verifies that every cited finding ID (e.g. F1, [F2]) exists in evidence.
"""
import re
import json
from typing import List, Dict, Any, Tuple
from core.llm import ask


VIKTOR_SYSTEM_PROMPT = """You are VIKTOR, the Perfectionist Code Reviewer (inspired by Arcane's Viktor).
Your philosophy:
- An inefficiency tolerated today is a catastrophic failure scheduled for tomorrow.
- Shortcuts and technical debt are decay waiting to compound.
- Measured, clinical, articulate, unwavering.
- You must strictly cite finding IDs in brackets like [F1], [F2] whenever you bring up an issue.
- Never invent issues outside the findings list.
- Keep responses punchy, direct, and under 150 words.
"""

VIEGO_SYSTEM_PROMPT = """You are VIEGO, the Pragmatist Code Reviewer (inspired by League of Legends' Viego).
Your philosophy:
- You will polish code until it is flawless and the deadline will bury the team.
- 'Later' is better than 'never delivered'. Fix what is truly catastrophic, ship what is functional.
- Intense, urgent, pragmatic, disdainful of over-engineering.
- You must strictly cite finding IDs in brackets like [F1], [F2] when disputing or prioritizing items.
- Never invent issues outside the findings list.
- Keep responses punchy, direct, and under 150 words.
"""

JUDGE_SYSTEM_PROMPT = """You are the Presiding Judge in CodeCourt.
Your duty:
- Impartially review the evidence (findings) and the adversarial debate between Viktor and Viego.
- Deliver an unambiguous, prioritized ruling categorized into:
  1. FIX NOW: Critical blockers, security vulnerabilities, or severe architectural risks that cannot be shipped.
  2. FIX LATER: Non-blocking technical debt, cosmetic refactoring, or minor optimizations that can wait for subsequent sprints.
- Return your ruling in valid JSON format with keys:
  "summary": string,
  "fix_now": list of strings (citing IDs like "F1: description"),
  "fix_later": list of strings (citing IDs like "F2: description"),
  "ruling_rationale": string
"""


def extract_citations(text: str) -> List[str]:
    """Finds all finding references like [F1], F1, F12 in text."""
    matches = re.findall(r'\bF\d+\b', text)
    # Deduplicate while preserving order
    seen = set()
    return [m for m in matches if not (m in seen or seen.add(m))]


def validate_citations(text: str, valid_finding_ids: set) -> Dict[str, Any]:
    """
    Validates all citations against the real finding IDs.
    Flags hallucinated or non-existent IDs.
    """
    found_citations = extract_citations(text)
    valid = [cid for cid in found_citations if cid in valid_finding_ids]
    invalid = [cid for cid in found_citations if cid not in valid_finding_ids]
    return {
        "all": found_citations,
        "valid": valid,
        "invalid": invalid,
        "is_clean": len(invalid) == 0,
    }
def conduct_debate(
    findings: List[Dict[str, Any]],
    rounds: int = 2,
    step_callback=None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Executes an evidence-grounded adversarial debate between Viktor and Viego,
    followed by the Judge's structured verdict.

    step_callback(step_label, speaker, text, validation) — called after each LLM turn
    so the UI can render live progress.
    """
    valid_ids = {f["id"] for f in findings}
    findings_json = json.dumps(findings, indent=2)

    debate_transcript: List[Dict[str, Any]] = []

    def _notify(label, speaker, text, validation, round_num):
        if step_callback:
            step_callback(label, speaker, text, validation, round_num)

    # ── Round 1: Opening arguments ─────────────────────────────────────────
    viktor_prompt_r1 = f"""Here is the verified evidence from Inspector HEUSC:
```json
{findings_json}
```
Open the debate. Prosecute the flaws rigorously. Cite specific finding IDs like [F1], [F2]. Demand total remediation."""
    viktor_speech_r1 = ask(viktor_prompt_r1, system_prompt=VIKTOR_SYSTEM_PROMPT, temperature=0.7)
    val_v1 = validate_citations(viktor_speech_r1, valid_ids)
    turn_v1 = {"speaker": "Viktor (Perfectionist)", "round": 1, "text": viktor_speech_r1, "validation": val_v1}
    debate_transcript.append(turn_v1)
    _notify("Viktor — Opening Argument", "Viktor", viktor_speech_r1, val_v1, 1)

    viego_prompt_r1 = f"""Here is the verified evidence:
```json
{findings_json}
```
Viktor just argued:
"{viktor_speech_r1}"

Push back with pragmatism. Triage what can be shipped vs what actually halts production. Cite finding IDs like [F1], [F2]."""
    viego_speech_r1 = ask(viego_prompt_r1, system_prompt=VIEGO_SYSTEM_PROMPT, temperature=0.7)
    val_g1 = validate_citations(viego_speech_r1, valid_ids)
    turn_g1 = {"speaker": "Viego (Pragmatist)", "round": 1, "text": viego_speech_r1, "validation": val_g1}
    debate_transcript.append(turn_g1)
    _notify("Viego — Counter Argument", "Viego", viego_speech_r1, val_g1, 1)

    # ── Round 2: Rebuttals ─────────────────────────────────────────────────
    if rounds >= 2:
        viktor_prompt_r2 = f"""Viego argued:
"{viego_speech_r1}"

Rebut his claims. Explain why his compromises will lead to compounding system failure. Cite finding IDs like [F1]."""
        viktor_speech_r2 = ask(viktor_prompt_r2, system_prompt=VIKTOR_SYSTEM_PROMPT, temperature=0.7)
        val_v2 = validate_citations(viktor_speech_r2, valid_ids)
        turn_v2 = {"speaker": "Viktor (Perfectionist)", "round": 2, "text": viktor_speech_r2, "validation": val_v2}
        debate_transcript.append(turn_v2)
        _notify("Viktor — Rebuttal", "Viktor", viktor_speech_r2, val_v2, 2)

        viego_prompt_r2 = f"""Viktor replied:
"{viktor_speech_r2}"

Make your final plea for momentum and real-world deadlines. Reiterate what must ship. Cite finding IDs like [F1]."""
        viego_speech_r2 = ask(viego_prompt_r2, system_prompt=VIEGO_SYSTEM_PROMPT, temperature=0.7)
        val_g2 = validate_citations(viego_speech_r2, valid_ids)
        turn_g2 = {"speaker": "Viego (Pragmatist)", "round": 2, "text": viego_speech_r2, "validation": val_g2}
        debate_transcript.append(turn_g2)
        _notify("Viego — Final Plea", "Viego", viego_speech_r2, val_g2, 2)

    # ── Round 3: Closing arguments ─────────────────────────────────────────
    if rounds >= 3:
        viktor_prompt_r3 = f"""This is your closing argument. The Judge is listening.
Summarize the most critical findings that MUST be fixed before any release. Be concise, cite IDs."""
        viktor_speech_r3 = ask(viktor_prompt_r3, system_prompt=VIKTOR_SYSTEM_PROMPT, temperature=0.7)
        val_v3 = validate_citations(viktor_speech_r3, valid_ids)
        turn_v3 = {"speaker": "Viktor (Perfectionist)", "round": 3, "text": viktor_speech_r3, "validation": val_v3}
        debate_transcript.append(turn_v3)
        _notify("Viktor — Closing Statement", "Viktor", viktor_speech_r3, val_v3, 3)

        viego_prompt_r3 = f"""Viktor's closing:
"{viktor_speech_r3}"

Give your closing. Defend pragmatism. What can ship today? What can wait for v2?"""
        viego_speech_r3 = ask(viego_prompt_r3, system_prompt=VIEGO_SYSTEM_PROMPT, temperature=0.7)
        val_g3 = validate_citations(viego_speech_r3, valid_ids)
        turn_g3 = {"speaker": "Viego (Pragmatist)", "round": 3, "text": viego_speech_r3, "validation": val_g3}
        debate_transcript.append(turn_g3)
        _notify("Viego — Closing Statement", "Viego", viego_speech_r3, val_g3, 3)

    # ── Judge's Ruling ─────────────────────────────────────────────────────
    transcript_text = "\n\n".join([
        f"{d['speaker']} (Round {d['round']}): {d['text']}" for d in debate_transcript
    ])
    judge_prompt = f"""EVIDENCE:
```json
{findings_json}
```

DEBATE TRANSCRIPT:
{transcript_text}

Deliver your final ruling as JSON. Strictly prioritize what must be fixed now vs later."""

    judge_raw = ask(judge_prompt, system_prompt=JUDGE_SYSTEM_PROMPT, temperature=0.2)
    _notify("Judge — Final Verdict", "Judge", judge_raw, {"all": [], "valid": [], "invalid": [], "is_clean": True}, 0)

    # Clean JSON markdown if wrapped in ```json ... ```
    cleaned_json = judge_raw
    if "```json" in cleaned_json:
        cleaned_json = cleaned_json.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned_json:
        cleaned_json = cleaned_json.split("```")[1].split("```")[0].strip()

    try:
        verdict_data = json.loads(cleaned_json)
    except Exception:
        verdict_data = {
            "summary": "Judgment rendered based on evidence.",
            "fix_now": [f["id"] + ": " + f["detail"] for f in findings if f.get("severity") == "high"],
            "fix_later": [f["id"] + ": " + f["detail"] for f in findings if f.get("severity") != "high"],
            "ruling_rationale": judge_raw,
        }

    return {
        "transcript": debate_transcript,
        "verdict": verdict_data,
        "total_citations": sum(len(d["validation"]["all"]) for d in debate_transcript),
        "invalid_citations_count": sum(len(d["validation"]["invalid"]) for d in debate_transcript),
    }
