# GPG-Signed Commit

Create a GPG-signed git commit following project conventions.

## Arguments

$ARGUMENTS - Optional commit message. If empty, a message will be drafted from the diff.

## Instructions

### Step 1: Check GPG Agent

Verify the GPG signing key is available:
```bash
gpg --list-secret-keys --keyid-format long 2>&1 | head -20
```

If the key is not found or GPG agent is not running, warn the user and suggest:
```bash
gpg-connect-agent reloadagent /bye
```

### Step 2: Analyze Changes

Run these commands to understand what will be committed:
```bash
cd /mnt/scratch_nvme/work/fabrictestbed-extensions
git status 2>&1
git diff --stat 2>&1
git diff --staged --stat 2>&1
```

If there are no changes (staged or unstaged), report "Nothing to commit" and stop.

### Step 3: Safety Checks

Before staging, check for files that should NOT be committed:
- `.env` files — NEVER commit these
- `id_token.json`, `*.pem`, `*_key` — credential files
- `__pycache__/`, `*.pyc` — build artifacts
- `.tokens.json` — authentication tokens

If any sensitive files are in the diff, warn the user and exclude them.

### Step 4: Stage Files

Stage files by name (NOT `git add -A` or `git add .`):
```bash
git add <specific-files>
```

If files are already staged, use those. Otherwise, stage all modified tracked files
that are safe to commit.

### Step 5: Match Commit Style

Read recent commits to match the project's style:
```bash
git log --oneline -10 2>&1
```

### Step 6: Draft Commit Message

If no message was provided in $ARGUMENTS:
1. Analyze the staged diff: `git diff --staged 2>&1`
2. Draft a concise message that:
   - Summarizes the "why" not the "what"
   - Uses imperative mood ("Add feature" not "Added feature")
   - Keeps the first line under 72 characters
   - Matches the style of recent commits

### Step 7: Create the Signed Commit

ALWAYS use the `-S` flag to explicitly GPG-sign:
```bash
git commit -S -m "$(cat <<'EOF'
<commit message>

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

NEVER use `--no-gpg-sign` or `-c commit.gpgsign=false`.

If the GPG signing fails (passphrase prompt, agent issue), suggest:
```bash
# Restart GPG agent
gpg-connect-agent reloadagent /bye

# Test signing
echo "test" | gpg --clearsign
```

### Step 8: Verify Signature

After the commit succeeds, verify the GPG signature:
```bash
git log --show-signature -1 2>&1
git log -1 --format='%H %G? %GK %GS' 2>&1
```

Report the verification result:
- `G` = Good signature
- `B` = Bad signature
- `U` = Good signature, untrusted key
- `N` = No signature
- `E` = Cannot check signature (missing key)

### Step 9: Report

```
Commit Summary
==============
Hash:       <short hash>
Message:    <commit message>
GPG Signed: YES (key: 68D279E0BD93F510)
Signature:  <verification status>
Files:      <count> files changed

Staged files:
  - <file list>
```

## Important Rules

1. ALWAYS sign with `-S` — this project requires GPG-signed commits for CI
2. NEVER commit `.env`, credential files, or tokens
3. NEVER use `git add -A` — stage specific files only
4. NEVER amend previous commits unless explicitly asked
5. NEVER push unless explicitly asked
6. If GPG signing fails, help debug — don't skip signing
