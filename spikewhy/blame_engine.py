"""
Blame Engine — correlates cost anomalies with PRs and uses LLM to reason about cause.
"""

import json
import os
import requests


ZAI_API_KEY = os.environ.get("ZAI_API_KEY", "")
ZAI_BASE = "https://api.z.ai/api/coding/paas/v4"


def build_prompt(anomaly: dict, candidates: list[dict]) -> str:
    """Build the LLM prompt for causal reasoning."""
    candidate_text = ""
    for i, c in enumerate(candidates, 1):
        pr = c.get("pr", {})
        scoring = c.get("scoring", {})
        candidate_text += f"""
Candidate {i}:
  PR #{pr.get('number', '?')}: "{pr.get('title', 'Unknown')}"
  Author: {pr.get('user', {}).get('login', 'unknown')}
  Merged: {pr.get('merged_at', 'unknown')}
  Cost-relevant keywords found: {', '.join(scoring.get('keywords', [])) or 'none'}
  Relevant diff lines:
{chr(10).join('    ' + l for l in scoring.get('relevant_lines', [])[:5]) or '    (no infrastructure changes detected)'}
"""

    return f"""You are a cloud cost analyst. A cost spike was detected and you need to identify the most likely cause.

COST SPIKE:
  Date: {anomaly['date']}
  Cost: ${anomaly['cost']} (normal avg: ${anomaly['avg']})
  Spike amount: +${anomaly['spike_amount']} ({anomaly['spike_ratio']}x normal)
  Most affected services: {', '.join(f"{k}: ${v}" for k, v in sorted(anomaly['services'].items(), key=lambda x: -x[1])[:3])}

RECENT DEPLOYS IN SPIKE WINDOW:
{candidate_text if candidate_text else "No deploys found in spike window."}

Based on the spike pattern and the deploy candidates, provide:
1. Most likely cause (which PR and why)
2. Confidence score (0-100%)
3. Specific change that likely caused it
4. Recommended action

Respond in this exact JSON format:
{{
  "blamed_pr": <PR number or null>,
  "blamed_author": "<github username or unknown>",
  "confidence": <0-100>,
  "cause": "<one sentence explanation>",
  "specific_change": "<what in the diff likely caused it>",
  "recommendation": "<one sentence fix recommendation>"
}}"""


def get_llm_blame(prompt: str) -> dict:
    """Call GLM-5 via Z.AI for causal reasoning."""
    if not ZAI_API_KEY:
        return {
            "blamed_pr": None,
            "blamed_author": "unknown",
            "confidence": 0,
            "cause": "LLM not configured — set ZAI_API_KEY",
            "specific_change": "N/A",
            "recommendation": "Set ZAI_API_KEY environment variable"
        }

    try:
        resp = requests.post(
            f"{ZAI_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {ZAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "glm-5",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except Exception as e:
        pass

    return {
        "blamed_pr": None,
        "blamed_author": "unknown",
        "confidence": 30,
        "cause": "Could not parse LLM response",
        "specific_change": "Manual investigation required",
        "recommendation": "Check recent deploys manually"
    }


def run_blame(anomaly: dict, candidates: list[dict]) -> dict:
    """Full blame pipeline: score candidates + LLM reasoning."""
    # Sort candidates by cost-relevance score
    candidates.sort(key=lambda c: c.get("scoring", {}).get("score", 0), reverse=True)

    prompt = build_prompt(anomaly, candidates[:3])  # top 3 to LLM
    result = get_llm_blame(prompt)

    return {
        "anomaly": anomaly,
        "candidates": candidates,
        "blame": result,
    }
