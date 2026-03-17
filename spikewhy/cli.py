#!/usr/bin/env python3
"""
SpikeWhy CLI -- main entrypoint.

Usage:
  spikewhy --repo owner/repo --since 7d
  spikewhy --repo owner/repo --since 30d --output discord
  spikewhy --demo
"""

import argparse
import os
import sys

from .cost_simulator import generate_baseline, detect_anomalies
from .github_poller import get_workflow_runs, get_pr_for_run, get_pr_diff, score_diff, runs_in_window
from .blame_engine import run_blame
from .reporter import print_report, send_discord, output_json


def run_demo():
    """Run SpikeWhy against simulated cost data with no external API calls."""
    print("\nSpikeWhy -- Demo Mode (simulated cost data)\n")

    records = generate_baseline(days=30)
    anomalies = detect_anomalies(records)

    print(f"Generated 30 days of cost data")
    print(f"Detected {len(anomalies)} anomalies\n")

    for anomaly in anomalies:
        print(f"Spike on {anomaly['date']}: ${anomaly['cost']} ({anomaly['spike_ratio']}x normal)")

        demo_candidates = [
            {
                "run": {"id": "demo-run-1", "name": "Deploy to Production"},
                "pr": {
                    "number": 47,
                    "title": "feat: increase ECS task memory for better performance",
                    "user": {"login": "tashil"},
                    "merged_at": anomaly["date"] + "T13:42:00Z",
                    "html_url": "https://github.com/demo/repo/pull/47",
                },
                "scoring": {
                    "score": 4,
                    "keywords": ["memory", "ecs", "fargate", "desired"],
                    "relevant_lines": [
                        "+  memory = 4096  # was 512",
                        "+  cpu    = 2048  # was 256",
                        "+  desired_count = 4  # was 1",
                    ]
                }
            },
            {
                "run": {"id": "demo-run-2", "name": "Deploy Frontend"},
                "pr": {
                    "number": 46,
                    "title": "fix: update node version in Dockerfile",
                    "user": {"login": "alice"},
                    "merged_at": anomaly["date"] + "T10:15:00Z",
                    "html_url": "https://github.com/demo/repo/pull/46",
                },
                "scoring": {
                    "score": 0,
                    "keywords": [],
                    "relevant_lines": ["-FROM node:18", "+FROM node:20"]
                }
            }
        ]

        result = run_blame(anomaly, demo_candidates)
        print_report(result)


def run_live(repo: str, days: int, output: str):
    """Run SpikeWhy against real GitHub + simulated cost data."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN not set. Export it and retry.")
        sys.exit(1)

    print(f"\nSpikeWhy -- analysing {repo} (last {days} days)\n")

    print("Loading cost data (simulated)...")
    records = generate_baseline(days=days)
    anomalies = detect_anomalies(records)

    if not anomalies:
        print("No cost anomalies detected.")
        return

    print(f"{len(anomalies)} anomaly(s) detected\n")

    print("Fetching GitHub Actions runs...")
    runs = get_workflow_runs(repo, days=days)
    print(f"Found {len(runs)} successful runs\n")

    for anomaly in anomalies:
        print(f"Spike: {anomaly['date']} -- ${anomaly['cost']} ({anomaly['spike_ratio']}x normal)")

        window_runs = runs_in_window(runs, anomaly["date"], window_hours=24)
        print(f"Deploys in window: {len(window_runs)}")

        candidates = []
        for run in window_runs[:5]:
            pr = get_pr_for_run(repo, run)
            if not pr:
                continue
            diff = get_pr_diff(repo, pr["number"])
            scoring = score_diff(diff)
            candidates.append({"run": run, "pr": pr, "scoring": scoring})

        result = run_blame(anomaly, candidates)

        if output == "discord":
            send_discord(result)
        elif output == "json":
            output_json(result)
        else:
            print_report(result)


def main():
    parser = argparse.ArgumentParser(
        prog="spikewhy",
        description="Trace cloud cost spikes back to the PR that caused them."
    )
    parser.add_argument("--repo", help="GitHub repo (owner/repo)")
    parser.add_argument("--since", default="7d", help="Lookback window e.g. 7d, 30d (default: 7d)")
    parser.add_argument("--output", choices=["stdout", "discord", "json"], default="stdout")
    parser.add_argument("--demo", action="store_true", help="Run with simulated data (no API keys needed)")

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.repo:
        parser.print_help()
        sys.exit(1)

    days = int(args.since.replace("d", ""))
    run_live(args.repo, days, args.output)


if __name__ == "__main__":
    main()
