# TruffleHog Configuration Fix

**Date**: November 14, 2025
**Issue**: GitHub Actions failing with TruffleHog "BASE and HEAD commits are the same" error
**Status**: ✅ RESOLVED

---

## Problem Summary

GitHub Actions workflow `docs-validation.yml` was failing with the error:

```
Error: BASE and HEAD commits are the same. TruffleHog won't scan anything.
Error: Process completed with exit code 1.
```

## Root Cause

**Explicit Git References Causing Same-Commit Comparison**

### The Problem Configuration

**`.github/workflows/docs-validation.yml`** (INCORRECT):
```yaml
- name: Scan for secrets
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: ${{ github.event.repository.default_branch }}  # ❌ Resolves to "main"
    head: HEAD                                            # ❌ Points to main
    extra_args: --only-verified
```

### Why This Failed

1. **Push Event to Main Branch**:
   - Workflow triggered by push to `main`
   - `github.event.repository.default_branch` = `"main"`
   - `HEAD` = current commit on main (e.g., `ba06204`)

2. **Git Resolution**:
   ```bash
   base_commit=$(git rev-parse "main")    # ba06204a7e8f1429...
   head_commit=$(git rev-parse "HEAD")    # ba06204a7e8f1429...
   # Both resolve to THE SAME COMMIT
   ```

3. **TruffleHog Logic**:
   ```bash
   if [ "$base_commit" == "$head_commit" ]; then
     echo "::error::BASE and HEAD commits are the same"
     exit 1  # ❌ Workflow fails
   fi
   ```

### Why Explicit References Don't Work

When you specify `base` and `head` explicitly, TruffleHog uses them **literally** instead of auto-detecting from the GitHub event context. This breaks the comparison because:

- On `push` to main: `base=main` and `head=HEAD` point to the same commit
- On `pull_request`: You'd need `base=${{ github.base_ref }}` and `head=${{ github.head_ref }}`
- Different events require different reference strategies

## Solution

**Remove Explicit References → Enable Auto-Detection**

### The Correct Configuration

**`.github/workflows/docs-validation.yml`** (CORRECT):
```yaml
- name: Scan for secrets
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    extra_args: --only-verified
```

### Why Auto-Detection Works

TruffleHog's GitHub Action has built-in event detection logic:

**For `push` Events**:
```bash
if [ "push" == "push" ]; then
  HEAD=ba06204a7e8f1429f7433dde6476e269f0ec2017    # Current commit (github.sha)
  BASE=0bfe73b1ea6855aeb71addde2f60047303c97590   # Previous commit (github.event.before)
fi
```

**For `pull_request` Events**:
```bash
elif [ "push" == "pull_request" ]; then
  BASE=<PR base ref>    # Target branch
  HEAD=<PR head ref>    # Source branch
fi
```

**Benefits**:
- ✅ Automatically uses correct commit range for each event type
- ✅ No risk of same-commit comparison errors
- ✅ Works correctly for push, pull_request, workflow_dispatch events
- ✅ Simpler configuration with fewer opportunities for error

## Event-Specific Behavior

### Push Events
```yaml
# Auto-detected values:
# BASE = ${{ github.event.before }}      # Previous commit
# HEAD = ${{ github.sha }}                # Current commit
```

**Result**: Scans only the new commits in the push

### Pull Request Events
```yaml
# Auto-detected values:
# BASE = ${{ github.event.pull_request.base.sha }}  # Target branch
# HEAD = ${{ github.event.pull_request.head.sha }}  # Source branch
```

**Result**: Scans all commits in the PR

### Workflow Dispatch / Schedule Events
```yaml
# Auto-detected values:
# BASE = ""    # Empty (full repository scan)
# HEAD = ""    # Empty (full repository scan)
```

**Result**: Full repository scan

## Alternative Explicit Configuration

If you **must** use explicit references (not recommended), use GitHub context variables:

```yaml
- name: Scan for secrets
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: ${{ github.event.before }}    # Previous commit in push
    head: ${{ github.sha }}              # Current commit
    extra_args: --only-verified
```

**Limitations**:
- Only works for `push` events
- Requires separate configuration for `pull_request` events
- More complex, more error-prone
- Not necessary when auto-detection works perfectly

## Verification

After applying the fix, the workflow should:

✅ **No longer fail with same-commit error**
```bash
# Before (error):
Error: BASE and HEAD commits are the same. TruffleHog won't scan anything.

# After (success):
🐷🔑🐷  TruffleHog. Unearth your secrets. 🐷🔑🐷
Scanning commits from 0bfe73b1...ba06204a
No verified secrets found
```

✅ **Correctly scan commit ranges**
```bash
# Push event:
Scanning commits: 0bfe73b1 (previous) → ba06204a (current)

# Pull request:
Scanning commits: base_branch → feature_branch

# Manual trigger:
Scanning entire repository history
```

## Best Practices

### ✅ DO
- Let TruffleHog auto-detect commit ranges from GitHub events
- Use minimal configuration (path + extra_args only)
- Trust the action's built-in event handling logic

### ❌ DON'T
- Specify `base` and `head` unless you have a very specific reason
- Use static branch names like `base: main` or `head: HEAD`
- Mix push and pull_request logic in the same configuration

## Files Modified

- `.github/workflows/docs-validation.yml` - Removed explicit base/head parameters

## Related Documentation

- [TruffleHog GitHub Action](https://github.com/trufflesecurity/trufflehog#octocat-trufflehog-github-action)
- [GitHub Actions Context](https://docs.github.com/en/actions/learn-github-actions/contexts#github-context)
- [Git Commit Ranges](https://git-scm.com/book/en/v2/Git-Tools-Revision-Selection)

## Summary

**Problem**: Explicit git references caused same-commit comparison failure
**Solution**: Remove `base` and `head` parameters to enable auto-detection
**Result**: TruffleHog correctly scans commit ranges for all event types

This fix ensures secret scanning works reliably across push events, pull requests, and manual workflow triggers without configuration complexity.
