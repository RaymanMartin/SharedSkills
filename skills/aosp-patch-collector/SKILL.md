---
name: aosp-patch-collector
description: >
  Given a .diff or .patch file and an AOSP source root directory, extract all
  referenced source files from the AOSP tree, copy them into a folder named
  after the patch, and create a .zip archive alongside it. Missing files are
  reported at the end but do not abort the process.

  Also supports extracting files from a git commit: given a directory
  containing a git repository and a commit hash, collect all files touched by
  that commit and zip them up.

  Use this skill whenever the user provides a diff or patch file and wants to
  collect the affected AOSP source files, package related files from a patch,
  zip patch-related sources, or prepare a source bundle from a diff. Also
  trigger when the user specifies a git commit hash and a repo/project
  directory and wants to extract the changed files.
  Trigger even if the user just says "帮我把patch里的文件从AOSP里拿出来",
  "帮我把这个commit涉及的文件拿出来", or similar.
---

# AOSP Patch Collector

Two operating modes:

| Mode | Input | Output name |
|------|-------|-------------|
| **patch** | `.diff` / `.patch` file + AOSP root | `<patch_stem>/` + `<patch_stem>.zip` |
| **commit** | git repo directory + commit hash | `<short_sha>/` + `<short_sha>.zip` |

---

## Mode 1 — Patch / diff file

### When to use
The user provides a `.diff` or `.patch` file and an AOSP source root.

### Workflow

1. **Ask for the two paths** (if not already provided):
   - Path to the `.diff` or `.patch` file
   - Path to the AOSP source root (the top-level directory that contains
     `build/`, `frameworks/`, `vendor/`, etc.)

2. **Run the collector script:**

   ```bash
   python3 <skill_dir>/scripts/collect_files.py patch \
       "<path/to/file.patch>" \
       "<path/to/aosp_root>"
   ```

3. **What the script does:**
   - Parses every `--- a/…` / `+++ b/…` line in the diff to collect unique
     file paths (skipping `/dev/null`).
   - For each path, looks for `<aosp_root>/<path>`.
   - Copies found files to `<patch_dir>/<patch_stem>/` preserving the relative
     directory structure.
   - Runs `zip -r <patch_stem>.zip <patch_stem>/` in `<patch_dir>`.
   - Prints a list of any files that were **not** found.

### Example

```
User: 帮我把这个 patch 文件里的 AOSP 源码文件打包
      patch: /home/dev/patches/fix_audio.patch
      AOSP root: /home/dev/aosp

→ Output folder: /home/dev/patches/fix_audio/
→ Zip:           /home/dev/patches/fix_audio.zip
```

---

## Mode 2 — Git commit

### When to use
The user provides a directory (which is or contains a git repository) and a
commit hash (or ref such as `HEAD~1`). They want all files changed in that
commit extracted and zipped.

### Workflow

1. **Ask for the required information** (if not already provided):
   - Path to the git repository directory
   - Commit hash or ref (e.g. `a3f9c12`, `HEAD`, `HEAD~2`)
   - *(Optional)* Output directory (defaults to the repo directory itself)

2. **Run the collector script:**

   ```bash
   python3 <skill_dir>/scripts/collect_files.py commit \
       "<path/to/repo_dir>" \
       "<commit_hash_or_ref>" \
       [--output-dir "<path/to/output_dir>"]
   ```

3. **What the script does:**
   - Runs `git diff-tree --no-commit-id -r --name-only <commit>` to get all
     files touched by the commit.
   - Copies each found file into `<output_dir>/<short_sha>/` preserving the
     relative directory structure.
   - Runs `zip -r <short_sha>.zip <short_sha>/` in `<output_dir>`.
   - Prints a list of any files that were **not** found on disk (e.g., deleted
     files that no longer exist in the working tree).

4. **Report results** to the user:
   - Resolved short SHA used as the folder/zip name.
   - How many files were collected successfully.
   - Full path to the output folder and zip archive.
   - List of any missing files.

### Example

```
User: 帮我把 /home/dev/vendor/qcom 目录下 commit a3f9c12 涉及的文件拿出来
      repo: /home/dev/vendor/qcom
      commit: a3f9c12

→ Output folder: /home/dev/vendor/qcom/a3f9c12/
→ Zip:           /home/dev/vendor/qcom/a3f9c12.zip
```

---

## Error handling

| Situation | Behaviour |
|-----------|-----------|
| Diff file not found | Error, abort |
| AOSP root not found | Error, abort |
| Repo directory not found | Error, abort |
| Directory is not a git repo | Error, abort |
| Commit hash not found / invalid | Error, abort |
| Individual file missing in source tree | Skip, log, continue |
| `zip` not installed | Error with message |
| No paths found in diff / commit | Warning, nothing to do |

## Notes

- The `patch` sub-command handles both git-style diffs (`diff --git a/… b/…`)
  and plain unified diffs.
- The `commit` sub-command accepts any git ref (`HEAD`, `HEAD~3`, branch name,
  full or abbreviated SHA).
- Only **modified / existing** files are copied; deleted files (not present in
  the working tree) are reported as missing.
- The output folder is **recreated from scratch** on each run, so re-running
  with the same input is safe.
