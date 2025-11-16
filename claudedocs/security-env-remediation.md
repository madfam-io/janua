# Environment File Security Remediation

**Date**: November 15, 2025  
**Severity**: 🚨 **CRITICAL**  
**Status**: ⚠️ **IMMEDIATE ACTION REQUIRED**

## Issue Summary

Two environment configuration files are currently **tracked in git** and publicly committed:
- `apps/demo/.env.production`
- `apps/demo/.env.staging`

These files should NEVER be committed to version control as they may contain sensitive configuration.

## Current State

### Files in Git
```bash
$ git ls-tree -r HEAD --name-only | grep "\.env"
apps/demo/.env.production  # ❌ SHOULD NOT BE TRACKED
apps/demo/.env.staging     # ❌ SHOULD NOT BE TRACKED
.env.example              # ✅ OK (example file)
.env.production.example   # ✅ OK (example file)
```

### Files on Filesystem
```bash
apps/demo/.env             # ❌ Not tracked but exists
apps/demo/.env.local       # ❌ Not tracked but exists
apps/demo/.env.production  # ❌ Tracked in git
apps/demo/.env.staging     # ❌ Tracked in git
```

### .gitignore Status
✅ `.gitignore` correctly excludes:
```
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
```

❌ BUT does not exclude:
- `.env.production` (without .local suffix)
- `.env.staging`

## Security Risk Assessment

### Risk Level: **CRITICAL** (9/10)

**Potential Exposure**:
- ✅ **Good News**: Files contain only localhost URLs, no actual secrets
- ⚠️ **Concern**: Pattern establishes dangerous precedent
- 🔴 **Risk**: Future updates might add secrets to tracked files

### Content Analysis
```bash
# apps/demo/.env.production contains:
NEXT_PUBLIC_PLINTO_ENV=demo
NEXT_PUBLIC_DEMO_API_URL=http://localhost:4000
NEXT_PUBLIC_APP_URL=http://localhost:3001
```

**No sensitive secrets found**, but the files should still NOT be in git.

## Remediation Steps

### Immediate Actions (Required Now)

1. **Update .gitignore** to exclude all environment files:
   ```bash
   # Add to .gitignore
   .env*
   !.env*.example
   ```

2. **Remove from Git History** (use git-filter-repo or BFG):
   ```bash
   # Stop tracking the files
   git rm --cached apps/demo/.env.production
   git rm --cached apps/demo/.env.staging
   git commit -m "security: remove environment files from git tracking"
   ```

3. **Create Proper Examples**:
   - Rename tracked files to `.example` suffix
   - Commit example files
   - Keep actual env files locally only

4. **Verify Removal**:
   ```bash
   git ls-files | grep "\.env" | grep -v "\.example"
   # Should return NOTHING except examples
   ```

### Long-term Prevention

1. **Add pre-commit hook** to prevent env file commits:
   ```bash
   # .husky/pre-commit
   #!/bin/sh
   if git diff --cached --name-only | grep -E "\.env$|\.env\.local|\.env\.production|\.env\.staging"; then
     echo "❌ ERROR: Environment files detected in commit"
     echo "Files should not be committed to git"
     exit 1
   fi
   ```

2. **Document env file management**:
   - Update README with env file setup instructions
   - Create `apps/demo/.env.example` with all required vars
   - Document which vars are required vs optional

3. **Audit for other sensitive files**:
   ```bash
   git ls-tree -r HEAD --name-only | grep -E "(secret|credential|key|token|password)"
   ```

## Implementation Checklist

- [ ] Update `.gitignore` with comprehensive env exclusions
- [ ] Remove `apps/demo/.env.production` from git
- [ ] Remove `apps/demo/.env.staging` from git
- [ ] Create `apps/demo/.env.example` with safe defaults
- [ ] Add pre-commit hook for env file detection
- [ ] Document env setup in README
- [ ] Verify no secrets in git history (scan with tools like gitleaks)
- [ ] Update CI/CD to use environment-specific secrets management

## Commands to Execute

```bash
# 1. Update .gitignore
cat >> .gitignore << 'EOF'

# All environment files (except examples)
.env*
!.env*.example
EOF

# 2. Stop tracking files
git rm --cached apps/demo/.env.production
git rm --cached apps/demo/.env.staging

# 3. Create examples
cp apps/demo/.env.production apps/demo/.env.example
git add apps/demo/.env.example

# 4. Commit changes
git commit -m "security: remove environment files from tracking, add examples"

# 5. Verify
git ls-files | grep "\.env" | grep -v "example"
```

## References

- OWASP: [Sensitive Data Exposure](https://owasp.org/www-project-top-ten/2017/A3_2017-Sensitive_Data_Exposure)
- GitHub: [Removing sensitive data from repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- Tools: [gitleaks](https://github.com/gitleaks/gitleaks), [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

---

**Action Required**: Execute remediation steps immediately to prevent future secret exposure.
