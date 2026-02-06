# Feature request template (Forest note → GitHub issue)

## Minimum info to collect

- Feature: (one line)
- Use case: why this matters / what you’re trying to do
- Current workaround: (or “none”)
- Proposed solution: what it could look like

## Step 1: capture in Forest

```bash
cat <<'EOF' | forest capture --title "Feature: <description>" --stdin --tags "#project/forest,#feature/<area>"
FEATURE: <description>

USE CASE: <why this matters>
CURRENT WORKAROUND: <how you work around it today>
PROPOSED: <what the solution could look like>
EOF
```

## Step 2: promote to GitHub

```bash
gh issue create --repo bwl/forest --label enhancement --title "Feature: <description>" --body "$(cat <<'EOF'
## Use Case
<why this matters>

## Current Workaround
<how you work around it today, or "none">

## Proposed Solution
<what the solution could look like>

## Context
- Forest node: <short-id from capture>
EOF
)"
```
