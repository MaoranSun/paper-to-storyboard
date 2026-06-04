#!/usr/bin/env bash
# Install the paper-to-storyboard skill into Claude Code.
#
# Usage:
#   ./install.sh              # copy ./skill/ -> ~/.claude/skills/paper-to-storyboard/
#   ./install.sh --symlink    # symlink instead (edits in ./skill/ go live immediately)
#   ./install.sh --uninstall  # remove the installed skill
#
# After install, the skill is available to Claude Code as `paper-to-storyboard`.
# Python dependencies must be installed separately — see requirements.txt.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$REPO_DIR/skill"
DEST="$HOME/.claude/skills/paper-to-storyboard"

case "${1:-}" in
  --symlink)
    if [ -e "$DEST" ] && [ ! -L "$DEST" ]; then
      echo "ERROR: $DEST exists and is not a symlink. Remove it first or run ./install.sh --uninstall" >&2
      exit 1
    fi
    rm -f "$DEST"
    mkdir -p "$(dirname "$DEST")"
    ln -s "$SRC" "$DEST"
    echo "Symlinked $DEST -> $SRC"
    ;;
  --uninstall)
    if [ -L "$DEST" ]; then
      rm "$DEST"
      echo "Removed symlink at $DEST"
    elif [ -d "$DEST" ]; then
      rm -rf "$DEST"
      echo "Removed $DEST"
    else
      echo "Nothing installed at $DEST"
    fi
    ;;
  *)
    mkdir -p "$DEST"
    # rsync is preferred but fall back to cp -R if absent
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete --exclude='.DS_Store' "$SRC/" "$DEST/"
    else
      rm -rf "$DEST"
      cp -R "$SRC" "$DEST"
    fi
    echo "Installed skill to $DEST"
    echo
    echo "Next steps:"
    echo "  1. python3 -m venv .venv && source .venv/bin/activate"
    echo "  2. pip install -r requirements.txt"
    echo "  3. In Claude Code, ask: 'convert /path/to/paper.pdf to a storyboard'"
    ;;
esac
