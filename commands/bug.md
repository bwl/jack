---
name: bug
description: File a bug report on the Forest repo
allowed-tools: Bash
---

# File a Forest Bug Report

Guide the user through filing a structured bug report. Gather the following information conversationally:

1. **Symptom**: What went wrong? (one-line summary)
2. **Reproduction steps**: How to trigger the bug
3. **Expected behavior**: What should have happened
4. **Actual behavior**: What actually happened
5. **Context**: Forest version, OS, relevant config, any error output

## Workflow

### Step 1: Capture in Forest

Create a searchable node first:

```bash
cat <<'EOF' | forest capture --stdin --tags "#project/forest" "#bug/<area>"
BUG: <symptom>

REPRO:
1. <step>
2. <step>
3. <observe>

EXPECTED: <expected behavior>
ACTUAL: <actual behavior>

CONTEXT: <version, config, environment>
EOF
```

### Step 2: File on GitHub

Promote to a GitHub issue:

```bash
gh issue create --repo bwl/forest --label bug --title "Bug: <symptom>" --body "$(cat <<'EOF'
## Symptom
<one-line description>

## Reproduction
1. <step>
2. <step>
3. <observe>

## Expected
<what should happen>

## Actual
<what happened>

## Context
- Forest node: <short-id from capture>
- OS: <os>
- Forest version: <version>
EOF
)"
```

### Step 3: Confirm

Show the user the created issue URL and the Forest node ID for reference.
