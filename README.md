# Jack

A helpful lumberjack - your Forest knowledge base companion. Jack is a Claude Code persona that serves as the main point of contact between you and your [Forest](https://github.com/bwl/forest) knowledge base. He searches before speaking, captures what matters, and files issues when something's broken or missing.

## Prerequisites

- [Forest CLI](https://github.com/bwl/forest) installed and configured
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- [`gh` CLI](https://cli.github.com/) authenticated (for issue filing)

## Setup

```bash
# 1. Clone the repo
cd ~/Developer
git clone https://github.com/bwl/jack.git
cd jack

# 2. Symlink the lumberjack skill (usable from any project)
ln -sf "$(pwd)/skills/lumberjack" ~/.claude/skills/lumberjack

# 3. Symlink slash commands
ln -sf "$(pwd)/commands/bug.md" ~/.claude/commands/bug.md
ln -sf "$(pwd)/commands/feature.md" ~/.claude/commands/feature.md

# 4. Add permissions to your global settings
# Add these to ~/.claude/settings.local.json under permissions.allow:
#   "Bash(forest:*)"
#   "Bash(gh issue create:*)"
#   "Bash(gh issue list:*)"
#   "Bash(gh issue view:*)"
#   "Skill(lumberjack)"
```

## Usage

### As Jack (full persona)

```bash
cd ~/Developer/jack
claude
```

Jack picks up the `CLAUDE.md` persona and has full access to all workflows.

### As a skill (from any project)

The lumberjack skill works from any directory. Invoke it when you need to search or capture knowledge:

```
> /lumberjack what do we know about scoring?
> /lumberjack capture this pattern we just discovered
```

### Slash commands

```
> /bug                    # File a bug report on Forest
> /feature                # File a feature request on Forest
```

## Quick Start

```bash
# Search your knowledge base
forest search "authentication"

# Capture a learning
echo "Redis caching reduces API latency by 10x for repeated queries" | forest capture --stdin --tags "#project/myapp" "#pattern/caching"

# Explore connections
forest explore --search "caching"

# File a bug
# Use /bug in Claude Code, or:
gh issue create --repo bwl/forest --label bug --title "Bug: ..."
```

## License

MIT
