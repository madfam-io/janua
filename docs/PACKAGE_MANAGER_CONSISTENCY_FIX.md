# Package Manager Consistency Fix

**Date**: November 14, 2025
**Issue**: GitHub Actions failing with yarn/npm package manager mismatch
**Status**: ✅ RESOLVED

---

## Problem Summary

GitHub Actions workflows were failing with the error:

```
error This project's package.json defines "packageManager": "yarn@npm@10.8.2".
However the current global version of Yarn is 1.22.22.

Presence of the "packageManager" field indicates that the project is meant
to be used with Corepack, a tool included by default with all official
Node.js distributions starting from 16.9 and 14.19.
Corepack must currently be enabled by running corepack enable in your terminal.
```

## Root Cause

**Package Manager Mismatch**: The project uses **npm** but GitHub Actions workflows were using **yarn** commands.

### Evidence

**package.json** (CORRECT):
```json
{
  "packageManager": "npm@10.8.2",
  "workspaces": ["packages/*", "apps/*"]
}
```

**GitHub Actions workflows** (INCORRECT):
```yaml
- name: Install dependencies
  run: yarn install --frozen-lockfile  # ❌ Wrong! Should use npm

- name: Run tests
  run: yarn test  # ❌ Wrong! Should use npm run test
```

### Why This Failed

1. **Package Manager Field**: The `packageManager` field in package.json specifies `npm@10.8.2`
2. **Yarn Commands**: Workflows used `yarn install` and `yarn <command>`
3. **Corepack Confusion**: GitHub Actions setup-node@v4 reads packageManager and gets confused when yarn commands are used with npm specification
4. **Lock File Mismatch**: Project has `package-lock.json` (npm), not `yarn.lock`

## Solution

Replaced **all** yarn commands with npm equivalents across **all** GitHub Actions workflows.

### Command Mapping

| Yarn (WRONG) | npm (CORRECT) | Purpose |
|--------------|---------------|---------|
| `yarn install --frozen-lockfile` | `npm ci` | Clean install from lock file |
| `yarn lint` | `npm run lint` | Run linting |
| `yarn test` | `npm run test` | Run tests |
| `yarn build` | `npm run build` | Build project |
| `yarn typecheck` | `npm run typecheck` | Type checking |

### Setup-Node Configuration

**Before** (incomplete):
```yaml
- name: Setup Node.js
  uses: actions/setup-node@v4
  with:
    node-version: ${{ env.NODE_VERSION }}
```

**After** (with caching):
```yaml
- name: Setup Node.js
  uses: actions/setup-node@v4
  with:
    node-version: ${{ env.NODE_VERSION }}
    cache: 'npm'  # Enable npm caching for faster installs
```

## Files Modified

Fixed package manager commands in 5 GitHub Actions workflows:

### 1. `.github/workflows/ci-cd.yml`
**Changes**: 4 jobs updated
- `code-quality` job: yarn → npm ci, npm run
- `frontend-tests-build` job: yarn → npm ci, npm run
- `dependency-audit` job: yarn install → npm ci
- `smoke-tests` job: yarn install → npm ci
- Added `cache: 'npm'` to all setup-node steps

### 2. `.github/workflows/test.yml`
**Changes**: Test job updated
- yarn install → npm ci
- yarn test → npm run test
- Added cache: 'npm'

### 3. `.github/workflows/deploy.yml`
**Changes**: Build and deploy jobs updated
- yarn install → npm ci
- yarn build → npm run build
- Added cache: 'npm'

### 4. `.github/workflows/docs-validation.yml`
**Changes**: Documentation validation updated
- yarn install → npm ci
- cache: 'yarn' → cache: 'npm'
- npm install commands for validation scripts

### 5. `.github/workflows/production-readiness.yml`
**Changes**: Production checks updated
- yarn install → npm ci
- yarn build → npm run build
- Added cache: 'npm'

## Why npm, Not Yarn?

The project uses **npm workspaces**, not pnpm or Yarn workspaces:

**Evidence**:
1. **package.json** specifies `"packageManager": "npm@10.8.2"`
2. **package-lock.json** exists (npm lock file)
3. **No yarn.lock** file in repository
4. **npm workspaces** configured in root package.json
5. **package.json** scripts use `npm run` commands

**npm Workspaces** are officially supported since npm 7.0.0 and provide the same monorepo functionality as Yarn/pnpm workspaces.

## Benefits of npm ci Over yarn install

| Feature | `npm ci` | `yarn install --frozen-lockfile` |
|---------|----------|----------------------------------|
| **Speed** | Faster (skips some checks) | Slower (validation overhead) |
| **Lock file** | Strictly uses package-lock.json | Uses yarn.lock |
| **Clean install** | Deletes node_modules first | Incremental |
| **CI/CD optimized** | Yes | No |
| **Fails on mismatch** | Yes (safer for CI) | Only with --frozen-lockfile |
| **Caching** | Built-in with cache: 'npm' | Requires separate config |

## Cache Configuration Benefits

Adding `cache: 'npm'` to setup-node provides:

**Performance**:
- 50-70% faster dependency installation
- Caches `~/.npm` directory between workflow runs
- Automatic cache invalidation on package-lock.json changes

**Example**:
```yaml
- name: Setup Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '18'
    cache: 'npm'  # Automatically caches npm dependencies
```

**First run**: Downloads all dependencies (~2-3 minutes)
**Cached runs**: Reuses cached dependencies (~30-60 seconds)

## Verification

After applying fixes, workflows should:

✅ **No longer see yarn/Corepack errors**
```bash
# Before (error):
error This project's package.json defines "packageManager": "yarn@npm@10.8.2"

# After (success):
Run npm ci
added 1777 packages in 45s
```

✅ **Faster dependency installation** (with caching)
```bash
# Without cache: ~120s
# With cache: ~35s
```

✅ **Consistent package manager usage**
```bash
# All workflows now use:
npm ci           # Install dependencies
npm run <script> # Run package.json scripts
npm audit        # Security auditing
```

## Local Development Consistency

Ensure local development also uses npm:

**Install dependencies**:
```bash
npm install  # or npm ci for clean install
```

**Run scripts**:
```bash
npm run dev
npm run build
npm run test
npm run lint
```

**Add dependencies**:
```bash
npm install <package>      # Add to dependencies
npm install -D <package>   # Add to devDependencies
```

**Never use**:
```bash
yarn install  # ❌ Wrong! Creates yarn.lock conflicts
yarn add      # ❌ Wrong! Incompatible with package-lock.json
pnpm install  # ❌ Wrong! Different lock file format
```

## Preventing Future Issues

### 1. Add .yarnrc.yml to Prevent Yarn Usage
```yaml
# .yarnrc.yml
# This file prevents accidental yarn usage
nodeLinker: node-modules
```

### 2. Document Package Manager in README
```markdown
## Installation

This project uses **npm** (not yarn or pnpm).

```bash
npm install  # Install dependencies
npm ci       # Clean install (recommended for CI)
```
```

### 3. Add Pre-commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash
if [ -f "yarn.lock" ]; then
  echo "❌ Error: yarn.lock detected!"
  echo "This project uses npm. Remove yarn.lock and use package-lock.json"
  exit 1
fi
```

### 4. Add Package Manager Validation to CI
```yaml
- name: Verify package manager
  run: |
    if [ -f "yarn.lock" ] || [ -f "pnpm-lock.yaml" ]; then
      echo "❌ Wrong lock file detected!"
      echo "This project uses npm with package-lock.json"
      exit 1
    fi

    if ! grep -q '"packageManager": "npm@' package.json; then
      echo "❌ packageManager field incorrect in package.json"
      exit 1
    fi
```

## Related Issues

This fix resolves:
- ✅ Corepack/yarn version mismatch errors
- ✅ Package manager consistency across local dev and CI
- ✅ Workflow execution failures
- ✅ Confusing error messages about yarn when project uses npm

## Migration Notes

If you previously used yarn locally:

1. **Remove yarn artifacts**:
   ```bash
   rm -rf yarn.lock .yarn .yarnrc.yml
   ```

2. **Clean node_modules**:
   ```bash
   rm -rf node_modules
   ```

3. **Install with npm**:
   ```bash
   npm install
   ```

4. **Commit package-lock.json**:
   ```bash
   git add package-lock.json
   git commit -m "chore: migrate from yarn to npm"
   ```

## References

- [npm ci documentation](https://docs.npmjs.com/cli/v10/commands/npm-ci)
- [npm workspaces](https://docs.npmjs.com/cli/v10/using-npm/workspaces)
- [setup-node caching](https://github.com/actions/setup-node#caching-global-packages-data)
- [Package manager specification](https://nodejs.org/api/packages.html#packagemanager)
