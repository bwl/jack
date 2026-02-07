---
name: tags-cleanup
description: Analyze and clean up Forest knowledge base tags. Use when asked to "clean tags", "fix tags", "tag audit", "tag hygiene", or "normalize tags". Audits tag entropy, finds duplicates and format violations, then applies fixes via the Forest CLI.
user-invocable: true
allowed-tools: Bash(forest:*), Bash(python3:*), Read, Grep, Glob
argument-hint: [--dry-run]
---

# Tags Cleanup Skill

Analyze and normalize all tags in the Forest knowledge base to the canonical `namespace:value` format.

## Tag Schema

Canonical format: **`namespace:value`** — lowercase, hyphens for multi-word, colon separator, no `#` prefix.

| Namespace  | Purpose          | Examples                                      |
|------------|------------------|-----------------------------------------------|
| `project`  | Which project    | `project:kingdom`, `project:forest`           |
| `domain`   | Top-level domain | `domain:projects`, `domain:ideas`             |
| `tech`     | Technology       | `tech:rust`, `tech:python`, `tech:bevy`       |
| `status`   | Lifecycle        | `status:active`, `status:dormant`             |
| `category` | Project category | `category:roguelike`, `category:knowledge`    |
| `area`     | Feature area     | `area:cli`, `area:tags`                       |
| `bug`      | Bug reports      | `bug:tags-normalization`                      |
| `feature`  | Feature requests | `feature:templates`                           |
| `topic`    | Content topic    | `topic:worldbuilding`, `topic:ai`             |
| `pattern`  | Patterns         | `pattern:tooling`, `pattern:planning`         |

## Workflow

### Step 1: Audit current tags

Run `forest tags list --json` and analyze the output. Classify every tag into one of:

- **Clean**: already matches `namespace:value` with a valid namespace
- **Rename**: wrong format but has a clear canonical mapping (e.g., `#project/foo` → `project:foo`, `rust` → `tech:rust`)
- **Delete**: adds no value and should be removed from all nodes (e.g., `source:Developer`, `tech:unknown`, `category:misc`)
- **Ambiguous**: needs human decision

Report a summary table:

```
Tags Audit
──────────
Total tags:    N
Clean:         N (N%)
Need rename:   N
Need delete:   N
Ambiguous:     N
```

### Step 2: Build normalization map

For each non-clean tag, determine the action:

**Rename rules** (in priority order):
1. `#namespace/value` → `namespace:value` (strip `#`, replace `/` with `:`)
2. `namespace/value` → `namespace:value` (replace `/` with `:`)
3. Bare language names → `tech:` namespace (`rust` → `tech:rust`, `python` → `tech:python`)
4. Bare topic words → `topic:` namespace (`writing` → `topic:writing`)
5. Merge duplicates to canonical form (e.g., `#project/kingdom-rpg` + `#project/kingdom` → `project:kingdom`)
6. Multi-word values get hyphens (`layer builder` → `topic:layer-builder`)
7. Singular/plural merge to the more common form

**Delete rules:**
- Tags that carry no information (`source:Developer`, `tech:unknown`)
- Junk-drawer tags (`category:misc`)
- Garbage values (malformed status strings, empty `bug/`, empty `feature/`)

Present the full map to the user for confirmation before executing.

### Step 3: Execute changes

If `$ARGUMENTS` contains `--dry-run`, stop after Step 2.

Otherwise, after user confirmation:

**Renames** — use `forest tags rename`:
```bash
forest tags rename "old-tag" "new-tag"
```

This is a bulk operation — it renames the tag across all nodes that have it. If the target tag already exists on a node, Forest merges them.

**Deletions** — Forest has no bulk tag delete. For each tag to delete:
1. Search for nodes with that tag: `forest search "<tag>" --limit 5 --json`
2. For each found node, remove the tag: `forest tags remove <node-id> "<tag>"`
3. Repeat until no more nodes are found

Run renames first, then deletions.

### Step 4: Verify

Run `forest tags list --json` again and confirm:
- Zero tags with `#` prefix
- Zero tags with `/` separator (should all use `:`)
- Zero bare tags (no namespace)
- All namespaces are from the valid set

Report final counts.

## Important Notes

- **Always confirm before executing.** Show the full rename/delete plan and wait for approval.
- `forest tags rename` is the primary tool — it's bulk and handles merge conflicts.
- `forest tags remove <ref> <tag>` removes a single tag from a single node. There is no bulk delete.
- Semantic search may not find all nodes for a given tag. If a tag persists after deletion attempts, report it and move on rather than looping.
- Tags are case-sensitive in Forest. `Source:Developer` and `source:Developer` are different.
- Do not touch the SQLite database directly. All changes go through the Forest CLI.
