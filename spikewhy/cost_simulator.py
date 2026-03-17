"""
Cost Simulator — generates realistic AWS-like daily cost data.
In production this would be replaced by boto3 + AWS Cost Explorer API.
"""

import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate_baseline(days: int = 30, base: float = 120.0) -> list[dict]:
    """
    Generate realistic daily cost data with natural variance.
    Occasionally injects a spike to simulate real incidents.
    """
    random.seed(42)
    records = []
    now = datetime.now(timezone.utc)

    for i in range(days, 0, -1):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        # Natural variance ±15%
        variance = random.uniform(0.85, 1.15)
        cost = round(base * variance, 2)

        # Inject a spike on day 7 and day 21
        if i == 7:
            cost = round(base * random.uniform(2.8, 3.5), 2)  # big spike
        if i == 21:
            cost = round(base * random.uniform(1.6, 2.0), 2)  # medium spike

        records.append({
            "date": date,
            "total_cost": cost,
            "services": {
                "EC2": round(cost * 0.45, 2),
                "RDS": round(cost * 0.20, 2),
                "S3": round(cost * 0.10, 2),
                "Lambda": round(cost * 0.08, 2),
                "ECS": round(cost * 0.12, 2),
                "Other": round(cost * 0.05, 2),
            }
        })

    return records


def detect_anomalies(records: list[dict], threshold: float = 1.5) -> list[dict]:
    """
    Flag days where cost exceeded threshold × 7-day rolling average.
    Returns list of anomaly dicts.
    """
    anomalies = []
    for i in range(7, len(records)):
        window = records[i - 7:i]
        avg = sum(r["total_cost"] for r in window) / 7
        current = records[i]["total_cost"]

        if current > avg * threshold:
            spike_amount = round(current - avg, 2)
            anomalies.append({
                "date": records[i]["date"],
                "cost": current,
                "avg": round(avg, 2),
                "spike_amount": spike_amount,
                "spike_ratio": round(current / avg, 2),
                "services": records[i]["services"],
            })

    return anomalies
