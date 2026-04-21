# Trunk-Based Development Skill

English | [中文](README.md)

Helps an assistant follow Trunk-Based Development practices: small batches, short-lived branches, and fast return to trunk.

## One-Line Pitch

Turn "work trunk-based" into an actionable Git workflow and avoid long-lived branches, oversized PRs, and delayed integration.

## Install

```bash
pnpx skills add leesama/skills --skill=trunk-based-development
```

## When to Use It

Use this skill when you want the assistant to work like this:

- "We use trunk-based development here."
- "Create a short-lived branch from `main` or `master`."
- "This task is too large. Split it into mergeable increments."
- "Hide unfinished work behind a feature flag and merge early."
- "Check whether this PR/change is too large."

## What This Skill Enforces

- Identify the real trunk branch before working
- Split work into independently verifiable, independently mergeable increments
- Prefer short-lived branches over long-running feature branches
- Sync with the latest trunk before merge when possible
- Land incomplete capabilities behind feature flags, hidden entry points, or disabled-by-default config
- Explain whether the change is small enough, mergeable on its own, and what verification gaps remain

## Typical Prompts

- "We use trunk-based development. Implement this task that way."
- "Create a short branch from main and keep the change mergeable."
- "Split this feature into three independent PRs."
- "Keep the new logic hidden behind a feature flag for now."
- "Review whether this branch still follows trunk-based development."

## Pairs Well With

- Creating short-lived branches
- Rebasing / syncing trunk
- Preparing small, clear PR descriptions
- Breaking large changes into increments

See [SKILL.md](SKILL.md) for the detailed workflow.
