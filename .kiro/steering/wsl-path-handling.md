---
inclusion: always
---

# WSL Environment — Path & Shell Handling Rules

This workspace lives on the **WSL2 (Ubuntu) filesystem** but Kiro runs on the
**Windows host**, so the agent's file/exec backend addresses the project through
the Windows UNC path. This triggers a known, actively-tracked Kiro bug
([Issue #5881 — Path Duplication in WSL](https://github.com/kirodotdev/Kiro/issues/5881)).
The rules below are the reliable working pattern, verified in this repo across a
full multi-phase task. Follow them for every file and shell operation.

## Project root

- **WSL (native, use this):** `/home/peter/projects/h-dcn`
- **Windows UNC (never use):** `\\wsl.localhost\Ubuntu\home\peter\projects\h-dcn`

## The bug, precisely

- The workspace root is registered as a UNC path (`\\wsl.localhost\Ubuntu\...`).
- The agent shell is **Windows PowerShell**, not a WSL bash shell. A user-opened
  terminal IS native WSL bash; the agent backend is not. They diverge.
- Symptoms observed here:
  1. **Path doubling** — an **absolute** path passed to file tools resolves to
     `//wsl.localhost/Ubuntu/home/peter/projects/h-dcn/home/peter/projects/h-dcn/...`
     → ENOENT.
  2. **Broken `cd` prepend** — every shell command gets a Windows-style
     `cd "\home\peter\..."` prepended, which fails
     (`-bash: cd: \home\...: No such file or directory`).
  3. **Stray junk tree** — a relative/backslash write can create a real
     `home/peter/projects/h-dcn/...` folder inside the repo.
  4. **Intermittent stalls** — commands return empty output / exit -1 when the
     WSL file backend (LxssManager/9P) hiccups.

## FILE TOOL RULES

1. **Always use workspace-RELATIVE paths** with file tools (`readFile`,
   `listDirectory`, `strReplace`, `fsWrite`, `grepSearch`, `fileSearch`).
   Example: `backend/tests/requirements.txt` — NOT
   `/home/peter/projects/h-dcn/backend/tests/requirements.txt`.
2. **NEVER pass an absolute path or a UNC path** to a file tool — that is what
   doubles.
3. If a file tool still returns a doubled `//wsl.localhost/...` path or ENOENT,
   **fall back to a WSL shell command** (see below) instead of retrying the tool.
4. `grepSearch`/`fileSearch` are generally reliable here (with relative
   `includePattern`s); prefer them for search over shell `grep`/`find`.

## SHELL (execute) RULES

1. **NEVER pass the `cwd` parameter.** Passing `cwd` triggers the broken
   `cd "\home\..."` prepend and makes commands return empty / exit -1. The
   shell already starts at `/home/peter/projects/h-dcn`. To run elsewhere, start
   the command string with a normal forward-slash `cd`, e.g.
   `cd backend && pytest ...`.
2. **Judge success by STDOUT/STDERR content, not the exit code.** Exit code is
   unreliable here (often -1 even on success). Read the actual output.
3. **Run each command once — do NOT retry in a loop.** If output is empty, it is
   usually a backend hiccup, not a real failure; re-read or reload rather than
   re-running blindly.
4. **Pipe `gh` and long/streamed output through `| cat`** (and set `GH_PAGER=cat`)
   to avoid the interactive spinner/pager hanging. Example:
   `GH_PAGER=cat gh run list --limit 5 | cat`.
5. **For long output that gets truncated mid-stream, redirect to an ABSOLUTE
   `/tmp/...` file, then read it back** (`cmd > /tmp/out.txt 2>&1; tail -n 40 /tmp/out.txt`).
   Never redirect to a repo-relative path with a backslash — that creates the
   junk `home/...` tree.
6. The shell executor is **PowerShell**; to run Linux tooling reliably, invoke
   the venv/binaries by explicit relative path (e.g. `backend/.venv/bin/python`)
   or prefix with `wsl` (`wsl cat path/to/file`) as a last-resort fallback.
7. **Never write files via shell redirect** when a file tool will do — but if you
   must, use an absolute `/tmp` path, not a repo-relative one.

## VENV / PYTHON NOTE

- The backend venv sets `PYTHONNOUSERSITE=1` (isolation). When calling it
  directly, prefix with `unset VIRTUAL_ENV;` and use `backend/.venv/bin/python`
  to avoid a stale `VIRTUAL_ENV` pointing at a deleted path.

## CLEANUP CHECK

- After operations that write files, verify no stray tree was created:
  check for `/home/peter/projects/h-dcn/home` and remove it if present
  (`rm -rf /home/peter/projects/h-dcn/home`). It should NOT exist.

## RECOVERY

- If the shell backend degrades (repeated empty/exit -1), **reload the Kiro
  window**; task state is on disk, nothing is lost.

## Status & references

- Tracking issue: [kirodotdev/Kiro#5881](https://github.com/kirodotdev/Kiro/issues/5881)
  (OPEN, high-priority). Related: #8424 (native WSL support), #4294 (terminal).
- Adapted from trevorbennett's community `wsl-paths.md`, refined with behavior
  verified in this repo (relative-vs-absolute nuance, the `cwd`/`cd` prepend, the
  `gh`/`| cat` and write-to-/tmp patterns).
- Proper fix (when Kiro's WSL-remote matures): run Kiro natively inside WSL so the
  agent backend is a WSL shell at `/home/...`. Currently unreliable (#4964) — do
  not depend on it yet.
