---
name: feature
description: File a feature request on the Forest repo
allowed-tools: Bash
---

# File a Forest Feature Request

Guide the user through filing a structured feature request. Gather the following information conversationally:

1. **Feature**: What capability is missing? (one-line summary)
2. **Use case**: Why does this matter? What are you trying to do?
3. **Current workaround**: How do you handle this today? (or "none")
4. **Proposed solution**: What could the solution look like?

## Workflow

### Step 1: Capture in Forest

Create a searchable node first:

```bash
cat <<'EOF' | forest capture --title "Feature: <description>" --stdin --tags "#project/forest,#feature/<area>"
FEATURE: <description>

USE CASE: <why this matters>
CURRENT WORKAROUND: <how you work around it today>
PROPOSED: <what the solution could look like>
EOF
```

### Step 2: File on GitHub

Promote to a GitHub issue:

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

### Step 3: Confirm

Show the user the created issue URL and the Forest node ID for reference.
