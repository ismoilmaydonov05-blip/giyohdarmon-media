#!/usr/bin/env bash
# Publishes the day's finished mp4 files on the throw-away branch `reels-media` (ONE orphan commit, force-pushed,
# nothing on main is touched) and prints public raw URLs pinned to the commit SHA (branch URLs can serve a cached 404).
#   push_media.sh <repo_dir> <YYYY-MM-DD> file1.mp4 [file2.mp4 ...]
set -euo pipefail
repo="$1"; day="$2"; shift 2
cd "$repo"
url=$(git remote get-url origin | sed -E 's#\.git$##')
slug=$(echo "$url" | sed -E 's#^.*github.com[:/]##')
export GIT_INDEX_FILE=$(mktemp -u)
git read-tree --empty
for f in "$@"; do
  blob=$(git hash-object -w "$f")
  git update-index --add --cacheinfo "100644,$blob,videos/$day/$(basename "$f")"
done
tree=$(git write-tree)
commit=$(GIT_AUTHOR_NAME=Claude GIT_AUTHOR_EMAIL=noreply@anthropic.com GIT_COMMITTER_NAME=Claude GIT_COMMITTER_EMAIL=noreply@anthropic.com \
  git commit-tree "$tree" -m "Reels media $day

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>")
rm -f "$GIT_INDEX_FILE"; unset GIT_INDEX_FILE
git push --force origin "$commit:refs/heads/reels-media" >&2
for f in "$@"; do echo "https://raw.githubusercontent.com/$slug/$commit/videos/$day/$(basename "$f")"; done
