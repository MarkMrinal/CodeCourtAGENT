"""
CodeCourt — Evidence-Grounded Multi-Agent Code Review.
Streamlit Web Application.
"""
import os
import json
import streamlit as st
from dotenv import load_dotenv

import importlib
import core.state
import core.inspector
import core.heusc_voice
import core.court
import core.llm
import demo.fix_runner

importlib.reload(core.llm)
importlib.reload(core.court)
importlib.reload(core.heusc_voice)
importlib.reload(core.inspector)
importlib.reload(core.state)

from core.state import create_initial_state, set_findings
from core.inspector import scan_directory, save_findings_to_json
from core.heusc_voice import speak_as_heusc, generate_scan_briefing
from core.court import conduct_debate
from core.llm import get_active_provider_info
from demo.fix_runner import execute_guided_fix, get_diff

load_dotenv(override=True)

# Streamlit Page Config
st.set_page_config(
    page_title="CodeCourt | Multi-Agent Code Review",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling — Premium Agentic Dark Theme
st.markdown("""
<style>
    /* ─── Base & Typography ─────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ─── Severity Badges ───────────────────────────────────────────── */
    .badge-high {
        background: linear-gradient(135deg, #ff4b4b22, #ff4b4b11);
        color: #ff6b6b;
        padding: 3px 10px;
        border-radius: 20px;
        border: 1px solid #ff4b4b66;
        font-weight: 600;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .badge-medium {
        background: linear-gradient(135deg, #ffa50022, #ffa50011);
        color: #ffb84d;
        padding: 3px 10px;
        border-radius: 20px;
        border: 1px solid #ffa50066;
        font-weight: 600;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .badge-low {
        background: linear-gradient(135deg, #00c0f222, #00c0f211);
        color: #33d1f5;
        padding: 3px 10px;
        border-radius: 20px;
        border: 1px solid #00c0f266;
        font-weight: 600;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* ─── Agent Cards ───────────────────────────────────────────────── */
    .agent-card {
        padding: 18px 20px;
        border-radius: 12px;
        margin-bottom: 14px;
        border-left: 4px solid;
        backdrop-filter: blur(8px);
        line-height: 1.6;
        transition: all 0.2s ease;
    }
    .agent-card:hover {
        transform: translateX(3px);
    }

    .viktor-card {
        background: linear-gradient(135deg, #1e1e2f 0%, #16162a 100%);
        border-left-color: #6366f1;
        box-shadow: 0 4px 20px rgba(99,102,241,0.12);
    }
    .viego-card {
        background: linear-gradient(135deg, #142420 0%, #0f1f1a 100%);
        border-left-color: #10b981;
        box-shadow: 0 4px 20px rgba(16,185,129,0.12);
    }
    .heusc-card {
        background: linear-gradient(135deg, #1f2a15 0%, #192310 100%);
        border-left-color: #84cc16;
        box-shadow: 0 4px 20px rgba(132,204,22,0.10);
    }
    .judge-card {
        background: linear-gradient(135deg, #2a2010 0%, #1f1808 100%);
        border-left-color: #eab308;
        box-shadow: 0 4px 24px rgba(234,179,8,0.18);
    }

    /* ─── Agent Step Progress Row ───────────────────────────────────── */
    .step-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 6px;
        font-size: 0.9rem;
        font-weight: 500;
    }
    .step-pending {
        background: #1e1e2e;
        color: #666;
        border: 1px solid #333;
    }
    .step-active {
        background: linear-gradient(90deg, #1a1a3e, #16162a);
        color: #a5b4fc;
        border: 1px solid #4f46e5;
        animation: pulse-border 1.5s infinite;
    }
    .step-done-viktor {
        background: linear-gradient(90deg, #16162a, #12122a);
        color: #a5b4fc;
        border: 1px solid #3730a3;
    }
    .step-done-viego {
        background: linear-gradient(90deg, #0f2a1e, #0a2015);
        color: #6ee7b7;
        border: 1px solid #059669;
    }
    .step-done-judge {
        background: linear-gradient(90deg, #2a2010, #221a08);
        color: #fde68a;
        border: 1px solid #d97706;
    }

    @keyframes pulse-border {
        0% { box-shadow: 0 0 0 0 rgba(99,102,241,0.4); }
        70% { box-shadow: 0 0 0 6px rgba(99,102,241,0); }
        100% { box-shadow: 0 0 0 0 rgba(99,102,241,0); }
    }

    /* ─── Courtroom Header Banner ───────────────────────────────────── */
    .court-banner {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border: 1px solid #4f46e5;
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 24px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(79,70,229,0.2);
    }
    .court-banner h2 {
        font-size: 1.6rem;
        font-weight: 700;
        background: linear-gradient(90deg, #818cf8, #a78bfa, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 6px 0;
    }
    .court-banner p {
        color: #9ca3af;
        margin: 0;
        font-size: 0.9rem;
    }

    /* ─── Citation Pill Tags ────────────────────────────────────────── */
    .citation-valid {
        display: inline-block;
        background: rgba(16,185,129,0.15);
        color: #34d399;
        border: 1px solid #059669;
        border-radius: 4px;
        padding: 1px 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        margin: 0 2px;
    }
    .citation-invalid {
        display: inline-block;
        background: rgba(239,68,68,0.15);
        color: #f87171;
        border: 1px solid #dc2626;
        border-radius: 4px;
        padding: 1px 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        margin: 0 2px;
    }

    /* ─── Verdict Section ───────────────────────────────────────────── */
    .verdict-fix-now {
        background: linear-gradient(135deg, #2a0a0a, #1f0808);
        border: 1px solid #991b1b;
        border-radius: 12px;
        padding: 16px 20px;
    }
    .verdict-fix-later {
        background: linear-gradient(135deg, #1a1a0a, #141408);
        border: 1px solid #854d0e;
        border-radius: 12px;
        padding: 16px 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "court_state" not in st.session_state:
    st.session_state.court_state = create_initial_state()
if "heusc_briefing" not in st.session_state:
    st.session_state.heusc_briefing = None
if "heusc_chat" not in st.session_state:
    st.session_state.heusc_chat = []

state = st.session_state.court_state

# Sidebar
with st.sidebar:
    st.title("⚖️ CodeCourt")
    st.caption("Evidence-grounded code intelligence")
    
    def get_secret(key: str, default: str = "") -> str:
        val = os.getenv(key, "")
        if val:
            return val.strip()
        try:
            if hasattr(st, "secrets") and key in st.secrets:
                return str(st.secrets[key]).strip()
        except Exception:
            pass
        return default

    gemini_key = get_secret("GEMINI_API_KEY")
    gemini_active = bool(gemini_key and not gemini_key.startswith("AQ.your_"))
    nv_key = get_secret("NVIDIA_API_KEY")
    nv_active = bool(nv_key and not nv_key.startswith("nvapi-your_"))
    groq_key = get_secret("GROQ_API_KEY")
    groq_active = bool(groq_key and not groq_key.startswith("gsk_your_"))

    if gemini_active:
        st.success("🟢 Google Gemini: Active (Primary)\n`gemini-flash-lite-latest`")
    elif nv_active:
        st.success("🟢 NVIDIA NIM: Active\n`z-ai/glm-5.3-flash`")
    elif groq_active:
        st.success("🟢 Groq: Active\n`qwen/qwen3.8-27b`")
    else:
        st.warning("🟡 LLM API: Not configured")
        st.info("Add GEMINI_API_KEY, NVIDIA_API_KEY, or GROQ_API_KEY to `.env` or Secrets.")

    st.markdown("---")
    st.subheader("Session State")
    st.write(f"**Target:** `{state.get('project_path') or 'None'}`")
    st.write(f"**Verified Findings:** `{len(state.get('findings', []))}`")
    st.write(f"**Verdict:** `{'Rendered' if state.get('verdict') else 'Pending'}`")

    if st.button("🔄 Reset Session", use_container_width=True):
        st.session_state.court_state = create_initial_state()
        st.session_state.heusc_briefing = None
        st.session_state.heusc_chat = []
        st.rerun()

    st.markdown("---")
    st.markdown("""
    **Architecture Guardrail:**
    - **HEUSC**: 100% deterministic (AST + Radon)
    - **Court**: Viktor vs. Viego (OpenRouter LLM)
    - **Citation Validator**: Mathematical verification of finding IDs
    """)

# Main Tabs
tab_inspector, tab_court, tab_demo = st.tabs([
    "🔍 HEUSC Inspector",
    "⚔️ The Court (Viktor vs Viego)",
    "🧪 Guided Fix Demo (Phase 3.5)"
])

# ==========================================
# TAB 1: HEUSC INSPECTOR
# ==========================================
with tab_inspector:
    st.header("HEUSC — The Inspector")
    st.markdown(
        "*Gathers measurable evidence. Rule-based, zero AI hallucination. "
        "Every finding receives a deterministic ID (`F1`, `F2`...).*"
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        target_input = st.text_input(
            "Scan Target (Local Path or Public GitHub Repo URL):",
            value="sample_project",
            placeholder="e.g. sample_project or https://github.com/psf/requests"
        )
    with col2:
        st.write("")
        st.write("")
        run_scan = st.button("🚀 Run HEUSC Scan", use_container_width=True, type="primary")

    if run_scan and target_input:
        with st.spinner("HEUSC is inspecting codebase structure and calculating metrics..."):
            try:
                findings = scan_directory(target_input)
                set_findings(state, findings)
                state["project_path"] = target_input
                save_findings_to_json(findings)
                
                # Generate Butler briefing
                briefing = generate_scan_briefing(findings)
                st.session_state.heusc_briefing = briefing
                st.success(f"Scan complete. {len(findings)} findings recorded in evidence repository.")
            except Exception as e:
                st.error(f"Inspection error: {e}")

    # Display Findings if available
    findings = state.get("findings", [])
    if findings:
        # Butler Briefing Card
        if st.session_state.heusc_briefing:
            st.markdown(f"""
            <div class="agent-card heusc-card">
                <b>🎩 HEUSC:</b><br/>
                <i>"{st.session_state.heusc_briefing}"</i>
            </div>
            """, unsafe_allow_html=True)

        # Metric summary row
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Total Findings", len(findings))
        col_m2.metric("High Severity", sum(1 for f in findings if f["severity"] == "high"))
        col_m3.metric("Medium Severity", sum(1 for f in findings if f["severity"] == "medium"))
        col_m4.metric("Audited Files", len({f["file"] for f in findings}))

        st.subheader("Verified Evidence Table (`findings.json`)")
        for f in findings:
            sev_class = f"badge-{f['severity']}"
            with st.expander(f"[{f['id']}] {f['issue']} in `{f['file']}` ({f['function']})"):
                st.markdown(f"**Severity:** <span class='{sev_class}'>{f['severity'].upper()}</span>", unsafe_allow_html=True)
                st.markdown(f"**Location:** `{f['file']}` → `def {f['function']}`")
                st.markdown(f"**Detail:** {f['detail']}")
                if f.get("metric"):
                    st.markdown(f"**Metric:** `{f['metric']}`")

        # Conversational Voice Layer
        st.markdown("---")
        st.subheader("💬 Speak with HEUSC (Voice Layer)")
        st.caption("HEUSC's voice layer is restricted strictly to the evidence above. It cannot fabricate new claims.")
        
        user_msg = st.text_input("Ask HEUSC about these findings:", placeholder="e.g. Which issue poses the biggest security threat?")
        if st.button("Send to HEUSC") and user_msg:
            with st.spinner("HEUSC is formulating a response..."):
                try:
                    reply = speak_as_heusc(user_msg, findings)
                    st.session_state.heusc_chat.append({"user": user_msg, "heusc": reply})
                except Exception as e:
                    st.error(f"HEUSC Voice error: {e}")

        for chat in reversed(st.session_state.heusc_chat):
            st.markdown(f"**You:** {chat['user']}")
            st.markdown(f"""
            <div class="agent-card heusc-card">
                <b>🎩 HEUSC:</b> {chat['heusc']}
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# TAB 2: THE COURT
# ==========================================
with tab_court:
    # Courtroom banner header
    st.markdown("""
    <div class="court-banner">
        <h2>⚔️ CodeCourt — The Adversarial Chamber</h2>
        <p>Viktor (Perfectionist) vs Viego (Pragmatist) · Every claim must cite a verified Finding ID · Hallucinations flagged by Citation Validator</p>
    </div>
    """, unsafe_allow_html=True)

    findings = state.get("findings", [])
    if not findings:
        st.warning("⚠️ No evidence loaded yet. Run a scan in the **HEUSC Inspector** tab first.")
    else:
        # Evidence summary strip
        high = sum(1 for f in findings if f["severity"] == "high")
        med  = sum(1 for f in findings if f["severity"] == "medium")
        low  = sum(1 for f in findings if f["severity"] == "low")
        st.markdown(f"""
        <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;">
            <div style="background:#1e1e2f;border:1px solid #3730a3;border-radius:8px;padding:10px 18px;text-align:center;">
                <div style="font-size:1.4rem;font-weight:700;color:#a5b4fc;">{len(findings)}</div>
                <div style="font-size:0.75rem;color:#888;">Total Findings</div>
            </div>
            <div style="background:#2a0a0a;border:1px solid #991b1b;border-radius:8px;padding:10px 18px;text-align:center;">
                <div style="font-size:1.4rem;font-weight:700;color:#f87171;">{high}</div>
                <div style="font-size:0.75rem;color:#888;">High Severity</div>
            </div>
            <div style="background:#1a1500;border:1px solid #92400e;border-radius:8px;padding:10px 18px;text-align:center;">
                <div style="font-size:1.4rem;font-weight:700;color:#fbbf24;">{med}</div>
                <div style="font-size:0.75rem;color:#888;">Medium Severity</div>
            </div>
            <div style="background:#0a1a1a;border:1px solid #0e7490;border-radius:8px;padding:10px 18px;text-align:center;">
                <div style="font-size:1.4rem;font-weight:700;color:#38bdf8;">{low}</div>
                <div style="font-size:0.75rem;color:#888;">Low Severity</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            rounds = st.slider("Debate Rounds", min_value=1, max_value=3, value=2,
                               help="Each round = Viktor + Viego speak. More rounds = deeper debate, ~8-10s more per round.")
        with col_c2:
            st.write("")
            start_court = st.button("⚔️ Convene the Court", type="primary", use_container_width=True)

        if start_court:
            # Build the agenda of steps to show
            steps = ["⚙️ Viktor — Opening Argument", "🗡️ Viego — Counter Argument"]
            if rounds >= 2:
                steps += ["⚙️ Viktor — Rebuttal", "🗡️ Viego — Final Plea"]
            if rounds >= 3:
                steps += ["⚙️ Viktor — Closing Statement", "🗡️ Viego — Closing Statement"]
            steps.append("⚖️ Judge — Final Verdict")

            # Render initial step tracker (all pending)
            progress_area = st.empty()

            def render_steps(completed, active_idx):
                html = "<div style='margin:16px 0'>"
                for i, step in enumerate(steps):
                    if i < completed:
                        # determine done color
                        if "Viktor" in step:
                            cls = "step-done-viktor"
                        elif "Viego" in step:
                            cls = "step-done-viego"
                        else:
                            cls = "step-done-judge"
                        html += f'<div class="step-row {cls}">✅ {step}</div>'
                    elif i == active_idx:
                        html += f'<div class="step-row step-active">⏳ {step}</div>'
                    else:
                        html += f'<div class="step-row step-pending">○ {step}</div>'
                html += "</div>"
                return html

            progress_area.markdown(render_steps(0, 0), unsafe_allow_html=True)

            completed_steps = [0]

            def on_step(label, speaker, text, validation, round_num):
                completed_steps[0] += 1
                progress_area.markdown(
                    render_steps(completed_steps[0], completed_steps[0]),
                    unsafe_allow_html=True
                )

            try:
                try:
                    debate_res = conduct_debate(findings, rounds=rounds, step_callback=on_step)
                except TypeError as te:
                    if "step_callback" in str(te):
                        debate_res = conduct_debate(findings, rounds=rounds)
                    else:
                        raise te
                state["debate_transcript"] = debate_res["transcript"]
                state["verdict"] = debate_res["verdict"]
                state["debate_stats"] = {
                    "total_citations": debate_res["total_citations"],
                    "invalid_citations": debate_res["invalid_citations_count"],
                }
                # Final state — all done
                progress_area.markdown(render_steps(len(steps), len(steps)), unsafe_allow_html=True)
                st.success(f"✅ Debate concluded! {debate_res['total_citations']} citations verified · {debate_res['invalid_citations_count']} flagged as hallucinated")
            except Exception as e:
                progress_area.empty()
                st.error(f"Court debate failed: {e}")

    # ── Display Debate Transcript ──────────────────────────────────────────
    transcript = state.get("debate_transcript", [])
    if transcript:
        st.markdown("---")
        st.subheader("📜 Courtroom Transcript")

        for turn in transcript:
            speaker = turn["speaker"]
            is_viktor = "Viktor" in speaker
            is_judge = "Judge" in speaker
            if is_judge:
                card_class, avatar = "judge-card", "⚖️"
            elif is_viktor:
                card_class, avatar = "viktor-card", "⚙️"
            else:
                card_class, avatar = "viego-card", "🗡️"

            val = turn["validation"]
            valid_pills  = "".join([f'<span class="citation-valid">{c} ✓</span>' for c in val["valid"]])
            invalid_pills = "".join([f'<span class="citation-invalid">{c} ✗ INVALID</span>' for c in val["invalid"]])

            if val["all"]:
                cite_line = f"<div style='margin-top:10px;font-size:0.8rem;'>Citations: {valid_pills}{invalid_pills}</div>"
            else:
                cite_line = "<div style='margin-top:10px;font-size:0.78rem;color:#666;'><i>No finding IDs cited in this turn.</i></div>"

            round_badge = f"<span style='background:#ffffff18;border-radius:4px;padding:1px 7px;font-size:0.75rem;'>Round {turn['round']}</span>" if turn["round"] > 0 else ""

            st.markdown(f"""
            <div class="agent-card {card_class}">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span style="font-size:1.1rem;">{avatar}</span>
                    <b style="font-size:0.95rem;">{speaker}</b>
                    {round_badge}
                </div>
                <div style="color:#d1d5db;line-height:1.7;">{turn['text']}</div>
                {cite_line}
            </div>
            """, unsafe_allow_html=True)

    # ── Judge Verdict ──────────────────────────────────────────────────────
    verdict = state.get("verdict")
    if verdict:
        st.markdown("---")
        stats = state.get("debate_stats", {})
        total_c = stats.get("total_citations", 0)
        bad_c = stats.get("invalid_citations", 0)

        st.markdown(f"""
        <div class="agent-card judge-card">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
                <span style="font-size:1.3rem;">⚖️</span>
                <b style="font-size:1.05rem;color:#fde68a;">The Presiding Judge — Final Ruling</b>
                <span style="margin-left:auto;font-size:0.8rem;color:#888;">{total_c} citations · {bad_c} hallucinated</span>
            </div>
            <div style="color:#fef3c7;font-style:italic;line-height:1.7;border-left:2px solid #d9770680;padding-left:12px;">
                {verdict.get('summary', '')}
            </div>
            <div style="margin-top:12px;color:#d1d5db;line-height:1.7;font-size:0.9rem;">
                {verdict.get('ruling_rationale', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_now, col_later = st.columns(2)
        with col_now:
            fix_now_items = verdict.get("fix_now", [])
            items_html = "".join([
                f'<div style="margin:6px 0;padding:6px 10px;background:#ffffff0a;border-radius:6px;font-size:0.88rem;">🔴 {item}</div>'
                for item in fix_now_items
            ]) or "<div style='color:#888;font-size:0.85rem;'>No critical blockers identified.</div>"
            st.markdown(f"""
            <div class="verdict-fix-now">
                <div style="font-weight:700;color:#f87171;margin-bottom:10px;font-size:0.95rem;">🚨 FIX NOW — Critical Blockers</div>
                {items_html}
            </div>
            """, unsafe_allow_html=True)

        with col_later:
            fix_later_items = verdict.get("fix_later", [])
            items_html = "".join([
                f'<div style="margin:6px 0;padding:6px 10px;background:#ffffff0a;border-radius:6px;font-size:0.88rem;">🟡 {item}</div>'
                for item in fix_later_items
            ]) or "<div style='color:#888;font-size:0.85rem;'>No deferred items.</div>"
            st.markdown(f"""
            <div class="verdict-fix-later">
                <div style="font-weight:700;color:#fbbf24;margin-bottom:10px;font-size:0.95rem;">⏳ FIX LATER — Manageable Debt</div>
                {items_html}
            </div>
            """, unsafe_allow_html=True)




# ==========================================
# TAB 3: GUIDED FIX DEMO (PHASE 3.5)
# ==========================================
with tab_demo:
    st.header("🧪 Phase 3.5 — Guided Fix Demo")
    st.markdown(
        "Demonstrates the entire lifecycle on a pre-chosen SQL Injection vulnerability: "
        "**Vulnerability Discovery → Failed Test → Automated Patch → Verified Pass.**"
    )

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.subheader("Vulnerable Code (`demo/snippet.py`)")
        try:
            with open("demo/snippet.py", "r") as f:
                st.code(f.read(), language="python")
        except Exception:
            st.write("File not found.")

    with col_d2:
        st.subheader("Security Test (`demo/snippet_test.py`)")
        try:
            with open("demo/snippet_test.py", "r") as f:
                st.code(f.read(), language="python")
        except Exception:
            st.write("File not found.")

    st.markdown("---")
    if st.button("🚀 Execute Guided Fix Walkthrough", type="primary", use_container_width=True):
        with st.spinner("Executing end-to-end fix and verification..."):
            res = execute_guided_fix()
            
            st.subheader("Verification Results")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### Step 1: Pre-Patch Test Run")
                if not res["before"]["passed"]:
                    st.error("❌ Test Failed as Expected (Vulnerability Proved)")
                else:
                    st.warning("⚠️ Test passed unexpectedly before patch")
                st.code(res["before"]["stdout"] or res["before"]["stderr"], language="text")

            with c2:
                st.markdown("### Step 2: Post-Patch Test Run")
                if res["after"]["passed"]:
                    st.success("✅ Test Passed! Vulnerability Remediated")
                else:
                    st.error("❌ Test still failed after patch")
                st.code(res["after"]["stdout"] or res["after"]["stderr"], language="text")

            st.markdown("### Step 3: Patch Applied (Unified Diff)")
            st.code(res["diff"], language="diff")
