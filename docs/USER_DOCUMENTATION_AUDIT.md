# User Documentation Audit - docs.plinto.dev

**Date**: November 14, 2025
**Scope**: User-facing documentation (apps/landing + apps/docs)
**Status**: ⚠️ NEEDS UPDATES

---

## 🎯 Executive Summary

The user-facing documentation has comprehensive content but contains **API/SDK method mismatches** with the actual implementation. While the structure and examples are excellent, the code examples reference SDK methods that may not exist in the current implementation.

### Critical Issues Found
1. **SDK API Mismatches**: Documentation uses `plinto.auth.mfa.*` methods not found in SDK code
2. **Implementation Assumptions**: Examples assume API endpoints that need verification
3. **Package Names**: Uses `@plinto/typescript-sdk`, `@plinto/react-sdk` (need to verify these match actual package.json)

### Strengths
- ✅ Comprehensive MFA documentation (2,700+ lines)
- ✅ Clear code examples and integration guides
- ✅ Well-structured quickstart guide
- ✅ Multiple framework examples (Express, FastAPI, React)

---

## 📋 Detailed Findings

### 1. Landing Site (`apps/landing`)

#### Files Audited
- `app/docs/quickstart/page.tsx` - Quickstart guide
- `app/features/page.tsx` - Features showcase
- `app/pricing/page.tsx` - Pricing tiers
- `app/compare/page.tsx` - Competitor comparison

#### Issues Found

**SDK Installation Names** (apps/landing/app/docs/quickstart/page.tsx:34-50)
```typescript
// Documentation claims:
npm install @plinto/typescript-sdk
npm install @plinto/react-sdk
pip install plinto-sdk

// NEED TO VERIFY:
- Do these package names match package.json?
- Are packages published to npm/PyPI?
- Are version numbers consistent?
```

**API Method Assumptions** (apps/landing/app/docs/quickstart/page.tsx:78-95)
```typescript
// Documentation shows:
const plinto = new PlintoClient({
  apiUrl: process.env.PLINTO_API_URL,
  apiKey: process.env.PLINTO_API_KEY
});

// NEED TO VERIFY:
- Does PlintoClient constructor accept these params?
- Is apiKey authentication implemented?
- Are environment variables documented correctly?
```

**SDK Methods** (apps/landing/app/features/page.tsx:45-62)
```typescript
// Documentation shows:
await plinto.auth.signUp({...})
await plinto.auth.signIn({...})
await plinto.auth.enableMFA('totp', {...})

// NEED TO VERIFY:
- Do these methods exist in SDK?
- Are parameter shapes correct?
- Are return types accurate?
```

### 2. Docs Site (`apps/docs`)

#### Files Audited
- `content/guides/authentication/mfa.md` - Comprehensive MFA guide (2,750 lines)

#### Critical Issues

**MFA API Methods** (content/guides/authentication/mfa.md:32-43)
```typescript
// Documentation shows extensive MFA API:
plinto.auth.mfa.setup({...})
plinto.auth.mfa.verify({...})
plinto.auth.mfa.getStatus({...})
plinto.auth.mfa.disable({...})
plinto.auth.mfa.generateBackupCodes({...})
plinto.auth.mfa.webauthn.generateChallenge({...})
plinto.auth.mfa.webauthn.verify({...})

// CRITICAL:
- These methods are NOT found in actual SDK code
- Need to either:
  a) Implement these methods in SDK, OR
  b) Update documentation to match actual API
```

**Express/FastAPI Examples** (lines 100-500)
- Examples show server-side implementation patterns
- Assume endpoint structure not verified against actual API
- Rate limiting configuration may not match implementation

**React Components** (lines 668-1152)
- Complex MFA setup/challenge components
- Assume SDK methods that may not exist
- May need significant updates to work with actual API

---

## ✅ SDK API VERIFICATION COMPLETE

**CRITICAL**: Comprehensive SDK API verification has been completed. See detailed findings in:
- **[SDK_API_VERIFICATION_REPORT.md](./SDK_API_VERIFICATION_REPORT.md)** - Complete analysis

### Key Verification Results

**VERIFIED** (✅ Good News):
- Package name is correct: `@plinto/typescript-sdk`
- Core auth methods exist: `signUp()`, `signIn()`, `signOut()`, `refreshToken()`
- MFA basic methods exist: `enableMFA()`, `verifyMFA()`, `getMFAStatus()`, `disableMFA()`
- OAuth methods exist and work
- Passkey methods exist and work

**CRITICAL ISSUES FOUND** (❌ Bad News):
1. **MFA API Structure Mismatch**: Documentation uses `plinto.auth.mfa.*` namespace that does NOT exist
   - Affects: Entire 2,750-line MFA guide
   - Impact: 100% of MFA examples will fail
   - Status: 🔴 PUBLICATION BLOCKER

2. **Missing Method**: `verifyToken()` documented but does NOT exist
   - Affects: Quickstart auth middleware example
   - Fix: Use `getCurrentUser()` instead
   - Status: 🔴 CRITICAL

3. **Parameter Name Mismatch**: Documentation uses `apiUrl`, SDK uses `baseURL`
   - Affects: All initialization code
   - Fix: Global find/replace
   - Status: 🔴 CRITICAL

**See full report for**: Detailed method inventory, fix timeline, publication checklist

---

## 🔍 Original Accuracy Verification Checklist

### Package Names & Installation

**Check**:
1. Verify `package.json` in each SDK package
2. Confirm published package names on npm/PyPI
3. Validate installation commands actually work

**Files to Check**:
```
packages/typescript-sdk/package.json
packages/react-sdk/package.json
packages/python-sdk/setup.py
```

### SDK API Methods

**Check against actual SDK code**:
```
packages/typescript-sdk/src/*.ts
- Does PlintoClient exist?
- Does auth.signUp() exist?
- Does auth.signIn() exist?
- Does auth.mfa.* namespace exist?
```

### API Endpoints

**Verify these endpoints exist**:
```
POST /api/v1/auth/signup
POST /api/v1/auth/login
POST /api/auth/mfa/setup
POST /api/auth/mfa/verify
GET /api/auth/mfa/status
POST /api/auth/mfa/disable
```

**Check against**:
```
apps/api/app/routers/*.py
apps/api/app/sso/domain/routers/*.py
```

---

## 📊 Documentation Coverage

### Complete & Accurate ✅
- Project README (root)
- Quick Start guide
- Demo walkthrough
- Performance optimization docs
- Project roadmap and status

### Needs Verification ⚠️
- Landing site SDK examples
- Quickstart code snippets
- Features page code examples
- Pricing claims (tier limits)

### Needs Major Updates ❌
- MFA documentation (2,750 lines of potentially inaccurate API docs)
- SDK integration guides
- API reference documentation
- Code examples across all guides

---

## 🛠️ Recommended Actions

### Immediate (Before Publication)

**Priority 1: SDK API Verification**
1. Read all SDK source files (`packages/*/src/`)
2. Document actual exported methods and signatures
3. Compare against documentation claims
4. Create API mismatch report

**Priority 2: Package Name Verification**
1. Check all `package.json` and `setup.py` files
2. Verify names match documentation
3. Test installation commands locally
4. Update any mismatches

**Priority 3: API Endpoint Verification**
1. List all documented endpoints
2. Check against actual router files
3. Test each endpoint with curl/Postman
4. Update documentation for any mismatches

### Short-Term (Week 1)

**Fix Critical Documentation**
1. Update MFA guide with actual SDK methods
2. Revise quickstart with working code
3. Verify all features page examples
4. Test and validate pricing tier claims

**Create Validation Suite**
1. Automated tests for all doc examples
2. SDK method existence checks
3. Endpoint availability tests
4. Package installation validation

### Medium-Term (Week 2-4)

**Comprehensive Update**
1. Rewrite MFA documentation (if methods don't exist)
2. Add "Verified" badges to tested examples
3. Create SDK API reference from source
4. Add version-specific documentation

**Quality Assurance**
1. Technical review by SDK developers
2. User testing with actual documentation
3. Automated accuracy checking
4. Regular sync with codebase changes

---

## 📝 Documentation Quality Matrix

| Document | Structure | Examples | Accuracy | Status |
|----------|-----------|----------|----------|--------|
| Quickstart | ✅ Excellent | ✅ Clear | ⚠️ Unverified | Needs validation |
| Features Page | ✅ Excellent | ✅ Comprehensive | ⚠️ Unverified | Needs validation |
| MFA Guide | ✅ Excellent | ✅ Detailed | ❌ Likely Wrong | Needs rewrite |
| API Reference | ⚠️ Incomplete | ⚠️ Some gaps | ⚠️ Unverified | Needs expansion |
| SDK Guides | ⚠️ Scattered | ✅ Good | ⚠️ Unverified | Needs consolidation |

---

## 🎯 Validation Checklist

### Before Publishing Packages

- [ ] **Verify every SDK method** in documentation exists in code
- [ ] **Test every code example** for compilation/execution
- [ ] **Validate all API endpoints** are implemented
- [ ] **Check package names** match across all documentation
- [ ] **Test installation commands** on clean environment
- [ ] **Verify pricing tiers** match billing service configuration
- [ ] **Test MFA flows** end-to-end with actual API
- [ ] **Check framework versions** (React 18+, Node 18+, Python 3.9+)
- [ ] **Validate error messages** match actual API responses
- [ ] **Test rate limiting** configuration matches docs

### Documentation Testing Script

```bash
# 1. Package installation test
npm install @plinto/typescript-sdk
npm install @plinto/react-sdk
pip install plinto-sdk

# 2. SDK method existence test
node -e "const plinto = require('@plinto/typescript-sdk'); console.log(plinto)"

# 3. API endpoint test
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'

# 4. Code example compilation test
# Copy each example to temp file and run:
tsc example.ts --noEmit
python example.py --check
```

---

## 🚨 Critical Concerns

### 1. MFA Documentation Validity
The 2,750-line MFA guide is comprehensive and well-written BUT:
- Uses extensive `plinto.auth.mfa.*` API that may not exist
- Complex React components assume non-existent SDK methods
- WebAuthn integration shown but not verified in codebase
- Could mislead users if published without validation

**Recommendation**:
- Do NOT publish MFA guide until SDK API verified
- Either implement documented methods OR rewrite guide
- Add "Draft" or "Coming Soon" badge if methods planned

### 2. Quickstart Accuracy
The quickstart is the first thing new users see:
- Must have 100% working code
- Every command must execute successfully
- API calls must work on actual server
- SDK imports must resolve correctly

**Recommendation**:
- Manual test complete quickstart flow
- Record video walkthrough as validation
- Add automated test that runs quickstart steps
- User test with fresh developers

### 3. Package Publication Blockers
Documentation assumes packages are published:
- `npm install @plinto/typescript-sdk`
- `pip install plinto-sdk`

**CRITICAL**: Don't publish docs until packages are actually available, OR clearly state "Pre-release - coming soon"

---

## 📈 Documentation Improvement Plan

### Phase 1: Validation (Week 1)
**Goal**: Identify all inaccuracies

1. **SDK Audit** (2-3 days)
   - Read all SDK source code
   - Document actual API surface
   - Create method inventory
   - Compare with documentation claims

2. **API Audit** (1-2 days)
   - List all router endpoints
   - Test each endpoint
   - Document request/response shapes
   - Compare with documentation

3. **Package Audit** (1 day)
   - Check all package.json/setup.py files
   - Verify package names
   - Test installation locally
   - Document discrepancies

### Phase 2: Correction (Week 2)
**Goal**: Fix all critical inaccuracies

1. **Update Quickstart** (1 day)
   - Replace with verified working code
   - Test end-to-end
   - Add validation tests

2. **Update Features Page** (1 day)
   - Verify all code examples
   - Replace non-working examples
   - Add "Tested" badges

3. **MFA Guide Decision** (2-3 days)
   - IF methods exist: Verify and test
   - IF methods don't exist:
     - Option A: Implement methods (engineering task)
     - Option B: Rewrite guide with actual API
     - Option C: Mark as "Roadmap" and remove

### Phase 3: Enhancement (Week 3-4)
**Goal**: Add validation and quality measures

1. **Automated Testing** (3-4 days)
   - Create doc example test suite
   - Add CI/CD validation
   - Implement "last tested" dates

2. **API Reference** (2-3 days)
   - Generate from actual SDK code
   - Add auto-sync mechanism
   - Include TypeScript types

3. **User Testing** (2-3 days)
   - Get 3-5 developers to follow docs
   - Collect feedback
   - Iterate on issues

---

## 🎯 Success Criteria

**Documentation is ready for publication when**:
- ✅ 100% of code examples compile and execute
- ✅ All SDK methods documented exist in actual code
- ✅ All API endpoints documented are implemented
- ✅ Package installation commands work on clean machine
- ✅ At least 3 external developers successfully followed quickstart
- ✅ Automated tests validate all examples
- ✅ Version numbers align across docs and packages

---

## 📞 Next Steps

1. **Immediate**: Run SDK API verification script
2. **Today**: Check package names and installation
3. **This Week**: Test all quickstart code examples
4. **Before Publication**: Complete validation checklist

**Owner**: Documentation Team + SDK Developers
**Timeline**: 1-2 weeks before package publication
**Priority**: 🔴 CRITICAL - Blocks publication

---

**Audit Status**: ⚠️ **DO NOT PUBLISH** until validation complete
**Risk Level**: HIGH - Inaccurate docs will damage credibility
**Recommendation**: Implement validation phase before any public release
