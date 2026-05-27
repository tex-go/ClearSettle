#!/usr/bin/env bash
# tag-release.sh — bump VERSION, update package.json, commit, and push a signed tag.
#
# Usage:
#   ./scripts/tag-release.sh 1.2.0          # explicit version
#   ./scripts/tag-release.sh patch          # auto-increment patch (1.0.0 → 1.0.1)
#   ./scripts/tag-release.sh minor          # auto-increment minor (1.0.0 → 1.1.0)
#   ./scripts/tag-release.sh major          # auto-increment major (1.0.0 → 2.0.0)
#
# Requirements: git, jq, bash ≥ 4
# Run from the repository root on a clean working tree, on the main branch.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION_FILE="$ROOT/VERSION"
PACKAGE_JSON="$ROOT/clearsettle-app/frontend/package.json"

# ── Guard checks ─────────────────────────────────────────────────────────────

BRANCH=$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
  echo "ERROR: releases must be cut from main (currently on '$BRANCH')"
  exit 1
fi

if ! git -C "$ROOT" diff --quiet HEAD; then
  echo "ERROR: working tree is dirty — commit or stash changes first"
  exit 1
fi

# ── Parse existing version ────────────────────────────────────────────────────

CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

ARG="${1:-}"

case "$ARG" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
  [0-9]*.[0-9]*.[0-9]*)
    IFS='.' read -r MAJOR MINOR PATCH <<< "$ARG"
    ;;
  *)
    echo "Usage: $0 <version|major|minor|patch>"
    echo "  version must be in MAJOR.MINOR.PATCH format (e.g. 1.2.3)"
    exit 1
    ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
TAG="v${NEW_VERSION}"

echo "Current version : $CURRENT"
echo "New version     : $NEW_VERSION"
echo "Git tag         : $TAG"
echo ""
read -rp "Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

# ── Bump files ────────────────────────────────────────────────────────────────

echo "$NEW_VERSION" > "$VERSION_FILE"

if command -v jq &>/dev/null; then
  tmp=$(mktemp)
  jq --arg v "$NEW_VERSION" '.version = $v' "$PACKAGE_JSON" > "$tmp"
  mv "$tmp" "$PACKAGE_JSON"
else
  # fallback: sed — fragile but works for standard package.json
  sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$NEW_VERSION\"/" "$PACKAGE_JSON"
fi

# ── Commit + tag ──────────────────────────────────────────────────────────────

git -C "$ROOT" add "$VERSION_FILE" "$PACKAGE_JSON"
git -C "$ROOT" commit -m "chore: release $TAG"
git -C "$ROOT" tag -a "$TAG" -m "Release $TAG"

echo ""
echo "Created commit and tag $TAG locally."
echo ""
echo "Push with:"
echo "  git push origin main && git push origin $TAG"
echo ""
echo "This will trigger the 'Release' workflow which creates a GitHub Release"
echo "and deploys to production."
