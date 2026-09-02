#!/usr/bin/env python3
"""
Two modes:
  patch  – Parses a diff/patch file, finds the referenced source files in an
            AOSP tree, copies them into an output folder and zips it.
  commit – Given a directory containing a git repo and a commit hash, collects
            all files touched by that commit and zips them.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _copy_and_zip(file_paths: "list[str]", source_root: str,
                  output_dir: str) -> None:
    """Copy *file_paths* from *source_root* into *output_dir* then zip it."""
    base_name = os.path.basename(output_dir)
    zip_dir   = os.path.dirname(output_dir)

    # Remove existing output dir to start fresh
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    found: "list[str]" = []
    missing: "list[str]" = []

    for rel_path in file_paths:
        src = os.path.join(source_root, rel_path)
        if os.path.isfile(src):
            dst = os.path.join(output_dir, rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  [OK]      {rel_path}")
            found.append(rel_path)
        else:
            print(f"  [MISSING] {rel_path}")
            missing.append(rel_path)

    # Zip the output folder
    zip_path = output_dir + ".zip"
    result = subprocess.run(
        ["zip", "-r", zip_path, base_name],
        cwd=zip_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[ERROR] zip failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[DONE] Copied {len(found)} file(s) → {output_dir}/")
    print(f"[DONE] Zip created → {zip_path}")

    if missing:
        print(f"\n[WARN] {len(missing)} file(s) not found in source tree:")
        for p in missing:
            print(f"       {p}")


# ---------------------------------------------------------------------------
# Mode 1: patch / diff file
# ---------------------------------------------------------------------------

def parse_diff_paths(diff_path: str) -> "list[str]":
    """Extract unique file paths from a unified diff / git patch file."""
    paths: set = set()
    with open(diff_path, "r", errors="replace") as f:
        for line in f:
            # Match lines like:  --- a/path/to/file   or   +++ b/path/to/file
            m = re.match(r'^(?:---|\+\+\+)\s+[ab]/(.+)', line)
            if m:
                p = m.group(1).strip()
                if p != "/dev/null":
                    paths.add(p)
    return sorted(paths)


def cmd_patch(args: argparse.Namespace) -> None:
    diff_path = os.path.abspath(args.diff)
    aosp_root = os.path.abspath(args.aosp_root)

    if not os.path.isfile(diff_path):
        print(f"[ERROR] Diff/patch file not found: {diff_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(aosp_root):
        print(f"[ERROR] AOSP root not found: {aosp_root}", file=sys.stderr)
        sys.exit(1)

    base_name  = os.path.splitext(os.path.basename(diff_path))[0]
    output_dir = os.path.join(os.path.dirname(diff_path), base_name)

    print(f"[INFO] Parsing: {diff_path}")
    file_paths = parse_diff_paths(diff_path)

    if not file_paths:
        print("[WARN] No file paths found in the diff. Is this a valid unified diff?")
        sys.exit(0)

    print(f"[INFO] Found {len(file_paths)} unique path(s) in diff.")
    _copy_and_zip(file_paths, aosp_root, output_dir)


# ---------------------------------------------------------------------------
# Mode 2: git commit
# ---------------------------------------------------------------------------

def get_commit_paths(repo_dir: str, commit: str) -> "list[str]":
    """Return the list of files touched by *commit* inside *repo_dir*."""
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", commit],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[ERROR] git diff-tree failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    paths = [p.strip() for p in result.stdout.splitlines() if p.strip()]
    return sorted(paths)


def get_short_sha(repo_dir: str, commit: str) -> str:
    """Resolve *commit* to a short SHA (7 chars)."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", commit],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return commit[:12]   # fallback: first 12 chars of whatever was given
    return result.stdout.strip()


def cmd_commit(args: argparse.Namespace) -> None:
    repo_dir = os.path.abspath(args.repo_dir)
    commit   = args.commit.strip()

    if not os.path.isdir(repo_dir):
        print(f"[ERROR] Repository directory not found: {repo_dir}", file=sys.stderr)
        sys.exit(1)

    # Verify it is a git repo
    check = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        print(f"[ERROR] Not a git repository: {repo_dir}", file=sys.stderr)
        sys.exit(1)

    short_sha  = get_short_sha(repo_dir, commit)
    output_base = args.output_dir if args.output_dir else repo_dir
    output_dir  = os.path.join(os.path.abspath(output_base), short_sha)

    print(f"[INFO] Repository : {repo_dir}")
    print(f"[INFO] Commit     : {commit} (short: {short_sha})")

    file_paths = get_commit_paths(repo_dir, commit)

    if not file_paths:
        print("[WARN] No files found for this commit.")
        sys.exit(0)

    print(f"[INFO] Found {len(file_paths)} file(s) in commit.")
    _copy_and_zip(file_paths, repo_dir, output_dir)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect AOSP source files from a patch or a git commit."
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # -- patch sub-command (original behaviour) --
    p_patch = sub.add_parser(
        "patch",
        help="Collect files referenced in a .diff/.patch file from an AOSP tree."
    )
    p_patch.add_argument("diff",      help="Path to the .diff or .patch file")
    p_patch.add_argument("aosp_root", help="Path to the AOSP source root directory")

    # -- commit sub-command (new) --
    p_commit = sub.add_parser(
        "commit",
        help="Collect files touched by a specific git commit from a repository directory."
    )
    p_commit.add_argument("repo_dir", help="Path to the git repository (or sub-project) directory")
    p_commit.add_argument("commit",   help="Commit hash (full or abbreviated) or ref (e.g. HEAD~1)")
    p_commit.add_argument(
        "--output-dir", "-o",
        dest="output_dir",
        default=None,
        help="Directory where the output folder and zip are created "
             "(default: same as repo_dir)"
    )

    args = parser.parse_args()

    if args.mode == "patch":
        cmd_patch(args)
    elif args.mode == "commit":
        cmd_commit(args)


if __name__ == "__main__":
    main()
