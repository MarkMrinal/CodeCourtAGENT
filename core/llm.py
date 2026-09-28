"""
LLM abstraction layer for CodeCourt.
Hierarchy:
1. Google Gemini (Primary)
2. NVIDIA NIM Primary Key (Fallback 1)
3. NVIDIA NIM Backup Key (Fallback 2)
4. Groq (Last Option Fallback)
"""
import os
import re
import requests
from typing import Optional, Tuple
from dotenv import load_dotenv

# Ensure fresh reload of .env values on every run
load_dotenv(override=True)

DEFAULT_GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]

_ACTIVE_PROVIDER: Optional[str] = "Gemini"
_ACTIVE_MODEL: Optional[str] = DEFAULT_GEMINI_MODELS[0]

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _get_secret(key: str, default: str = "") -> str:
    """Retrieve configuration from .env or Streamlit Cloud Secrets."""
    # Always reload dotenv in case the file was modified
    load_dotenv(override=True)
    val = os.getenv(key, "")
    if val:
        return val.strip()
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return default


def _strip_thinking(text: str) -> str:
    """Remove reasoning/thinking artifacts that some models leak into output."""
    if not text:
        return ""
    text = _THINK_TAG_RE.sub("", text).strip()
    text = re.sub(r"```thinking.*?```", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    return text.strip()


def _call_gemini(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    api_key = _get_secret("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")

    models_to_try = [model] if model else DEFAULT_GEMINI_MODELS
    last_err = None

    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        global _ACTIVE_PROVIDER, _ACTIVE_MODEL
                        _ACTIVE_PROVIDER = "Gemini"
                        _ACTIVE_MODEL = m
                        return _strip_thinking(parts[0]["text"])
            else:
                last_err = Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            last_err = e
            continue

    if last_err:
        raise last_err
    raise RuntimeError("Gemini returned empty response.")


def _call_nvidia(
    api_key: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "z-ai/glm-5.3-flash",
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: int = 15,
) -> str:
    base_url = _get_secret("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code == 200:
        data = resp.json()
        raw = data["choices"][0]["message"]["content"] or ""
        return _strip_thinking(raw)
    raise RuntimeError(f"NVIDIA API HTTP {resp.status_code}: {resp.text[:200]}")


def _call_groq(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> str:
    from groq import Groq
    api_key = _get_secret("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not configured")

    client = Groq(api_key=api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=messages,
        temperature=temperature,
        max_tokens=min(max_tokens, 800),
    )
    raw = resp.choices[0].message.content or ""
    global _ACTIVE_PROVIDER, _ACTIVE_MODEL
    _ACTIVE_PROVIDER = "Groq"
    _ACTIVE_MODEL = "qwen/qwen3.8-27b"
    return _strip_thinking(raw)


def ask(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """
    Primary LLM entrypoint for CodeCourt with automatic multi-tier fallback:
    1. Gemini (Primary)
    2. NVIDIA Primary Key (Fallback 1)
    3. NVIDIA Backup Key (Fallback 2)
    4. Groq (Last option fallback)
    """
    errors = []

    # ── 1. Gemini (Primary) ────────────────────────────────────────────────
    gemini_key = _get_secret("GEMINI_API_KEY")
    if gemini_key:
        try:
            return _call_gemini(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            errors.append(f"Gemini: {e}")

    # ── 2. NVIDIA Primary Key (Fallback 1) ─────────────────────────────────
    nv_key = _get_secret("NVIDIA_API_KEY")
    nv_model = _get_secret("NVIDIA_MODEL", "z-ai/glm-5.3-flash")
    if nv_key:
        try:
            res = _call_nvidia(
                api_key=nv_key,
                prompt=prompt,
                system_prompt=system_prompt,
                model=nv_model,
                temperature=temperature,
                max_tokens=min(max_tokens, 1024),
                timeout=12,
            )
            global _ACTIVE_PROVIDER, _ACTIVE_MODEL
            _ACTIVE_PROVIDER = "NVIDIA (Primary)"
            _ACTIVE_MODEL = nv_model
            return res
        except Exception as e:
            errors.append(f"NVIDIA Primary: {e}")

    # ── 3. NVIDIA Backup Key (Fallback 2) ──────────────────────────────────
    nv_backup_key = _get_secret("NVIDIA_API_KEY_BACKUP")
    if nv_backup_key:
        try:
            res = _call_nvidia(
                api_key=nv_backup_key,
                prompt=prompt,
                system_prompt=system_prompt,
                model=nv_model,
                temperature=temperature,
                max_tokens=min(max_tokens, 1024),
                timeout=12,
            )
            _ACTIVE_PROVIDER = "NVIDIA (Backup)"
            _ACTIVE_MODEL = nv_model
            return res
        except Exception as e:
            errors.append(f"NVIDIA Backup: {e}")

    # ── 4. Groq (Last option) ──────────────────────────────────────────────
    groq_key = _get_secret("GROQ_API_KEY")
    if groq_key:
        try:
            return _call_groq(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=min(max_tokens, 800),
            )
        except Exception as e:
            errors.append(f"Groq: {e}")

    raise RuntimeError(f"All LLM providers failed:\n" + "\n".join(errors))


def get_active_provider_info() -> Tuple[Optional[str], Optional[str]]:
    """Returns currently active (provider, model)."""
    return _ACTIVE_PROVIDER or "Gemini", _ACTIVE_MODEL or DEFAULT_GEMINI_MODELS[0]
