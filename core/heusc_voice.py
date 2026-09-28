"""
HEUSC's Voice Layer.
The only AI part of HEUSC.
Used strictly for phrasing and conversational interactions.
STRICT CONSTRAINT: Never hallucinates or adds new findings.
Only rephrases the deterministic evidence present in findings.json.
"""
import json
from typing import List, Dict, Any, Optional
from core.llm import ask


HEUSC_VOICE_SYSTEM_PROMPT = """You are HEUSC, the hyper-competent, calm, and formal AI Butler Inspector (inspired by The Millionaire Detective – Balance: Unlimited).
Your demeanor:
- Unhurried, impeccably polite, razor-sharp, concise, and professional.
- You treat every scan like a completed case file.
- You NEVER invent or speculate about unverified issues.
- You strictly speak about the findings provided in the context.
- If no findings exist, you report that no evidence of irregularities was discovered.
- If asked a general question ("hello", "summarize the report"), answer in your calm persona while referencing the exact case findings.
"""


def format_findings_for_prompt(findings: List[Dict[str, Any]]) -> str:
    """Serializes findings into compact JSON for context grounding."""
    if not findings:
        return "No findings recorded. Codebase is clean."
    return json.dumps(findings, indent=2)


def speak_as_heusc(user_query: str, findings: List[Dict[str, Any]]) -> str:
    """
    Generate a conversational response from HEUSC grounded solely in existing findings.
    """
    evidence_block = format_findings_for_prompt(findings)
    prompt = f"""EVIDENCE ON RECORD (Strict Ground Truth):
```json
{evidence_block}
```

USER QUERY / COMMAND:
"{user_query}"

Respond as HEUSC. Ground every statement strictly in the EVIDENCE above. Never invent new issues or findings.
"""
    return ask(prompt=prompt, system_prompt=HEUSC_VOICE_SYSTEM_PROMPT, temperature=0.3)


def generate_scan_briefing(findings: List[Dict[str, Any]]) -> str:
    """
    Generates HEUSC's immediate post-scan briefing.
    """
    count = len(findings)
    if count == 0:
        return "Scan complete, sir. No irregularities or defects were detected in the inspected modules. The repository appears sound."

    high_count = sum(1 for f in findings if f.get("severity") == "high")
    med_count = sum(1 for f in findings if f.get("severity") == "medium")

    prompt = f"""The static scan has completed with {count} total findings:
- High severity: {high_count}
- Medium severity: {med_count}

Findings record:
{json.dumps(findings[:5], indent=2)}

Provide your formal, concise post-scan opening statement (2-3 sentences), in the style of HEUSC.
"""
    try:
        return ask(prompt=prompt, system_prompt=HEUSC_VOICE_SYSTEM_PROMPT, temperature=0.3)
    except Exception:
        # Fallback if Groq API is not yet configured
        return (
            f"Scan complete, sir. {count} matters warrant your attention, "
            f"{high_count} of them classified as high severity. "
            f"The evidence is ready for presentation or handoff to the Court."
        )
