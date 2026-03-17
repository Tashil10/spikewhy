"""
Reporter — formats and delivers blame reports to Discord or stdout.
"""

import json
import os
import requests


DISCORD_WEBHOOK = os.environ.get("SPIKEWHY_DISCORD_WEBHOOK", "")


def confidence_emoji(score: int) -> str:
    if score >= 80: return "🔴"
    if score >= 50: return "🟡"
    return "🟢"


def format_report(result: dict) -> str:
    anomaly = result["anomaly"]
    blame = result["blame"]
    candidates = result["candidates"]

    pr_str = f"PR #{blame['blamed_pr']}" if blame["blamed_pr"] else "Unknown PR"
    conf = blame.get("confidence", 0)
    emoji = confidence_emoji(conf)

    lines = [
        f"⚠️  **COST SPIKE DETECTED — {anomaly['date']}**",
        f"",
        f"💸  Spend: **${anomaly['cost']}** (avg: ${anomaly['avg']}, +${anomaly['spike_amount']} / {anomaly['spike_ratio']}x normal)",
        f"🔥  Top affected: {', '.join(f'{k} ${v}' for k, v in sorted(anomaly['services'].items(), key=lambda x: -x[1])[:3])}",
        f"",
        f"{emoji}  **Most likely cause:** {pr_str} by @{blame['blamed_author']}",
        f"📊  Confidence: **{conf}%**",
        f"🔍  Why: {blame['cause']}",
        f"⚙️   Change: {blame['specific_change']}",
        f"✅  Fix: {blame['recommendation']}",
    ]

    if candidates:
        lines.append(f"")
        lines.append(f"**Deploys investigated:** {len(candidates)}")
        for c in candidates[:3]:
            pr = c.get("pr", {})
            score = c.get("scoring", {}).get("score", 0)
            if pr:
                lines.append(f"  • PR #{pr.get('number')} — {pr.get('title', '?')[:50]} (cost signals: {score})")

    return "\n".join(lines)


def print_report(result: dict):
    """Print report to stdout."""
    print("\n" + "=" * 60)
    print(format_report(result))
    print("=" * 60 + "\n")


def send_discord(result: dict):
    """Send report to Discord webhook."""
    if not DISCORD_WEBHOOK:
        print("[reporter] No SPIKEWHY_DISCORD_WEBHOOK set, skipping Discord.")
        return

    text = format_report(result)
    resp = requests.post(DISCORD_WEBHOOK, json={"content": text}, timeout=10)
    if resp.status_code in (200, 204):
        print("[reporter] Discord alert sent.")
    else:
        print(f"[reporter] Discord failed: {resp.status_code} {resp.text}")


def output_json(result: dict):
    """Dump full result as JSON."""
    print(json.dumps(result, indent=2, default=str))
