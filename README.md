# ⚡ SpikeWhy

> Automatically trace cloud cost spikes back to the PR that caused them.

Most FinOps tools tell you *what* spiked. SpikeWhy tells you *why* — connecting your cloud bill directly to the commit that caused it.

---

## The Problem

Your AWS bill jumped $840 on Tuesday. You spend 3 hours manually cross-referencing:
- CloudWatch metrics
- GitHub deploy history  
- PR diffs
- Slack messages

SpikeWhy does this in seconds.

---

## How It Works

```
Cost spike detected
       ↓
Find deploys in spike window (GitHub Actions)
       ↓
Fetch PR diffs for those deploys
       ↓
Score diffs for infrastructure changes
       ↓
LLM reasons about most likely cause
       ↓
Report: "PR #47 by @tashil — ECS memory 512MB → 4096MB (87% confidence)"
```

---

## Quickstart

```bash
pip install spikewhy

# No API keys needed — try the demo first
spikewhy --demo

# Run against your real repo
export GITHUB_TOKEN=ghp_xxx
spikewhy --repo yourorg/yourrepo --since 7d

# Post to Discord
export SPIKEWHY_DISCORD_WEBHOOK=https://discord.com/api/webhooks/xxx
spikewhy --repo yourorg/yourrepo --since 7d --output discord
```

---

## Example Output

```
============================================================
⚠️  COST SPIKE DETECTED — 2026-03-10

💸  Spend: $342.18 (avg: $121.40, +$220.78 / 2.82x normal)
🔥  Top affected: ECS $154, EC2 $98, RDS $68

🔴  Most likely cause: PR #47 by @tashil
📊  Confidence: 87%
🔍  Why: ECS task definition changed memory from 512MB to 4096MB with desired_count increased from 1 to 4
⚙️   Change: memory = 4096, desired_count = 4
✅  Fix: Roll back ECS task definition memory to 512MB or reduce desired_count

Deploys investigated: 2
  • PR #47 — feat: increase ECS task memory for better performance (cost signals: 4)
  • PR #46 — fix: update node version in Dockerfile (cost signals: 0)
============================================================
```

---

## Configuration

| Environment Variable | Description | Required |
|---|---|---|
| `GITHUB_TOKEN` | GitHub personal access token (repo scope) | Yes (live mode) |
| `SPIKEWHY_DISCORD_WEBHOOK` | Discord webhook URL for alerts | No |
| `ZAI_API_KEY` | Z.AI API key for LLM reasoning | No (uses heuristics if unset) |

---

## Roadmap

- [x] Cost anomaly detection
- [x] GitHub Actions deploy correlation  
- [x] PR diff scoring
- [x] LLM causal reasoning
- [x] Discord alerts
- [ ] Real AWS Cost Explorer integration
- [ ] GitHub Action packaging
- [ ] Web dashboard
- [ ] Slack integration
- [ ] Multi-cloud (GCP, Azure)

---

## Why Not Just Use...

| Tool | What it does | What it misses |
|---|---|---|
| AWS Cost Explorer | Shows cost by service | No link to code changes |
| Infracost | Estimates cost before deploy | Doesn't track post-deploy actuals |
| Datadog | Metrics + anomaly detection | No PR/commit correlation |
| Vantage / Finout | FinOps dashboards | No engineering workflow integration |

SpikeWhy is the missing link.

---

## License

MIT
