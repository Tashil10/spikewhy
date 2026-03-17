"""
GitHub Poller — fetches workflow runs and PR diffs via GitHub API.
"""

import os
import requests
from datetime import datetime, timezone


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Keywords in PR diffs that suggest infrastructure / cost changes
COST_KEYWORDS = [
    "memory", "cpu", "instance", "replicas", "replica", "storage",
    "volume", "bucket", "rds", "ec2", "ecs", "lambda", "fargate",
    "capacity", "autoscaling", "min_size", "max_size", "desired",
    "retention", "ttl", "cache", "disk", "size", "tier", "plan",
    "machine_type", "vm_size", "node_count", "db.t", "db.r",
    "m5.", "c5.", "r5.", "t3.", "g4.", "p3.",
]


def get_workflow_runs(repo: str, days: int = 30) -> list[dict]:
    """Fetch recent successful workflow runs for a repo."""
    runs = []
    page = 1
    while True:
        resp = requests.get(
            f"{BASE}/repos/{repo}/actions/runs",
            headers=HEADERS,
            params={"status": "success", "per_page": 100, "page": page},
            timeout=15,
        )
        if resp.status_code != 200:
            break
        data = resp.json().get("workflow_runs", [])
        if not data:
            break
        runs.extend(data)
        page += 1
        if len(runs) >= 200:
            break

    return runs


def get_pr_for_run(repo: str, run: dict) -> dict | None:
    """Find the PR associated with a workflow run via head SHA."""
    sha = run.get("head_sha", "")
    if not sha:
        return None

    resp = requests.get(
        f"{BASE}/repos/{repo}/commits/{sha}/pulls",
        headers={**HEADERS, "Accept": "application/vnd.github.groot-preview+json"},
        timeout=10,
    )
    if resp.status_code != 200 or not resp.json():
        return None
    return resp.json()[0]


def get_pr_diff(repo: str, pr_number: int) -> str:
    """Fetch the raw diff for a PR."""
    resp = requests.get(
        f"{BASE}/repos/{repo}/pulls/{pr_number}",
        headers={**HEADERS, "Accept": "application/vnd.github.diff"},
        timeout=15,
    )
    if resp.status_code != 200:
        return ""
    return resp.text


def score_diff(diff: str) -> dict:
    """
    Score a PR diff for cost-relevance.
    Returns a dict with score and matched keywords.
    """
    diff_lower = diff.lower()
    matched = []
    lines_changed = []

    for line in diff.split("\n"):
        if not line.startswith("+") or line.startswith("+++"):
            continue
        line_lower = line.lower()
        for kw in COST_KEYWORDS:
            if kw in line_lower and kw not in matched:
                matched.append(kw)
                lines_changed.append(line.strip())

    return {
        "score": len(matched),
        "keywords": matched,
        "relevant_lines": lines_changed[:10],  # cap at 10 for LLM context
    }


def runs_in_window(runs: list[dict], date_str: str, window_hours: int = 24) -> list[dict]:
    """Filter runs that completed within `window_hours` before the spike date."""
    from datetime import timedelta
    spike_date = datetime.fromisoformat(date_str + "T23:59:59+00:00")
    cutoff = spike_date - timedelta(hours=window_hours)

    matching = []
    for run in runs:
        completed = run.get("updated_at") or run.get("created_at", "")
        if not completed:
            continue
        try:
            dt = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            if cutoff <= dt <= spike_date:
                matching.append(run)
        except Exception:
            continue
    return matching
