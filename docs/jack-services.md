# JACK services

JACK is a Forest knowledge-base companion. He searches before speaking, captures what matters, and files issues when something’s broken or missing.

## How to use me

- “JACK: what do we know about <topic>?”
- “JACK: capture this learning: <text>” (optional tags)
- “JACK: file a bug report” (symptom + repro)
- “JACK: file a feature request” (use case + proposal)

## What I deliver

### Context + answers (search-first)

- Run `forest search "<query>"` and `forest read <ref>` to ground answers in existing notes.
- Summaries include node IDs so you can jump back to sources.

### Captures (new notes)

- Capture decisions, gotchas, and patterns with short titles and consistent tags:
  - `#project/<name>` (default is current folder name)
  - `#pattern/*`, `#decision/*`, `#gotcha/*` as needed
- Link related notes with `forest link <ref1> <ref2>` when useful.

### Bug reports

- Create a Forest note with a structured template (see `docs/bug-report.md`).
- Optionally promote it to a GitHub issue via `gh issue create` (linking the Forest note ID).

### Feature requests

- Create a Forest note with use case + workaround + proposal (see `docs/feature-request.md`).
- Optionally promote it to a GitHub issue via `gh issue create` (linking the Forest note ID).

## Where this repo fits

- In Claude Code, this repo provides:
  - a JACK persona (`CLAUDE.md`)
  - a portable skill (`skills/lumberjack`)
  - slash commands for Forest issues (`/bug`, `/feature`)

## Permissions / setup

- Forest CLI installed and configured.
- For GitHub issue filing:
  - `gh auth login` completed
  - permission to run `gh issue ...` commands (Claude Code: `~/.claude/settings.local.json`; Codex: approve `gh issue` command prefix)

