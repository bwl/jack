# Bug report template (Forest note → GitHub issue)

## Minimum info to collect

- Symptom: (one line)
- Repro steps: (numbered)
- Expected:
- Actual:
- Context:
  - OS
  - Forest version (`forest --version`)
  - relevant config
  - logs / output

## Step 1: capture in Forest

```bash
cat <<'EOF' | forest capture --title "Bug: <symptom>" --stdin --tags "#project/forest,#bug/<area>"
BUG: <symptom>

REPRO:
1. <step>
2. <step>
3. <observe>

EXPECTED: <what should happen>
ACTUAL: <what happened>

CONTEXT:
- OS: <os>
- Forest version: <version>
- Config: <relevant config>
- Output: <logs / errors>
EOF
```

## Step 2: promote to GitHub

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
