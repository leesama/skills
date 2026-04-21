# Trunk-Based Development Skill

English | [中文](README.md)

Helps an assistant follow Trunk-Based Development practices: small batches, short-lived branches, fast return to trunk, and a hard rule that unfinished work must stay behind a feature flag.

## One-Line Pitch

Turn "work trunk-based" into an actionable Git workflow and avoid long-lived branches, oversized PRs, delayed integration, and unfinished code landing on trunk without a kill switch.

## Install

```bash
pnpx skills add leesama/skills --skill=trunk-based-development
```

## When to Use It

Use this skill when you want the assistant to work like this:

- "We use trunk-based development here."
- "Create a short-lived branch from `main` or `master`."
- "This task is too large. Split it into mergeable increments."
- "Create a feature flag first, then merge unfinished work early."
- "Check whether this PR/change is too large."

## What This Skill Enforces

- Identify the real trunk branch before working
- Split work into independently verifiable, independently mergeable increments
- Prefer short-lived branches over long-running feature branches
- Sync with the latest trunk before merge when possible
- Require a feature flag or equivalent disabled-by-default protection before unfinished work can land on trunk
- If the change cannot be safely turned off, keep splitting it until it can
- Explain whether the change is small enough, mergeable on its own, and what verification gaps remain

## Typical Prompts

- "We use trunk-based development. Implement this task that way."
- "Create a short branch from main and keep the change mergeable."
- "Split this feature into three independent PRs."
- "Do not expose the new logic yet. Add a feature flag first."
- "Review whether this branch still follows trunk-based development."

## Pairs Well With

- Creating short-lived branches
- Rebasing / syncing trunk
- Preparing small, clear PR descriptions
- Breaking large changes into increments

See [SKILL.md](SKILL.md) for the detailed workflow.
