# Root Cause Analysis: Plinto Marketing Website Issues

## Investigation Summary

After systematic investigation of the reported issues, I've identified the actual problems and their root causes.

## Issue 1: Pricing Page 404 - FALSE ALARM ✅

### **Root Cause Analysis**:
The pricing page 404 issue is **NOT REPRODUCIBLE** in the current codebase state.

### **Evidence**:
1. **Route exists**: `/Users/aldoruizluna/labspace/plinto/apps/marketing/app/pricing/page.tsx` ✅
2. **Component complete**: PricingSection, ComparisonSection, CTASection all exist ✅
3. **Dev server**: `HTTP/1.1 200 OK` at `http://localhost:3003/pricing` ✅
4. **Production build**: Successfully generates static pricing page ✅
5. **Production server**: `HTTP/1.1 200 OK` at `http://localhost:3000/pricing` ✅
6. **Navigation**: Link correctly configured in navigation.tsx ✅

### **Status**: **RESOLVED** - No action needed

---

## Issue 2: Playwright/Jest Conflict - CONFIRMED ❌

### **Root Cause Analysis**:
Jest is trying to run Playwright test files, causing the error "Playwright Test needs to be invoked via 'npx playwright test'".

### **Evidence**:
```
FAIL tests/focused-link-test.spec.ts
Playwright Test needs to be invoked via 'npx playwright test' and excluded from Jest test runs.
```

### **Additional Issues Found**:
1. **Jest configuration problems**: Many test files have malformed imports/exports
2. **Test environment issues**: `describe` and `jest` are undefined in some files
3. **Mixed test frameworks**: Playwright `.spec.ts` files in Jest test discovery path

### **Required Actions**:
1. ✅ Separate Playwright and Jest test directories
2. ✅ Update Jest configuration to exclude Playwright tests
3. ✅ Fix broken Jest test files
4. ✅ Add proper Playwright configuration
5. ✅ Update package.json scripts

---

## Additional Issues Discovered

### Issue 3: Jest Test Suite Failures - CRITICAL ❌

Multiple Jest tests are failing due to:
- Missing test setup configuration
- Incorrect component imports (lowercase vs uppercase)
- Missing test-id attributes in components
- Undefined `describe` and `jest` globals

### Issue 4: Missing Playwright Configuration

- No `playwright.config.ts` file found
- Playwright tests mixed with Jest tests causing conflicts

---

## Implementation Plan

### Phase 1: Separate Test Frameworks
1. Create dedicated `tests-e2e/` directory for Playwright tests
2. Move `tests/focused-link-test.spec.ts` to new location
3. Update Jest config to exclude e2e tests

### Phase 2: Fix Jest Configuration
1. Fix test environment setup
2. Correct component imports in test files
3. Add missing test-id attributes

### Phase 3: Configure Playwright Properly
1. Add `playwright.config.ts`
2. Update package.json scripts
3. Ensure proper separation

### Phase 4: Validation
1. Verify Jest tests run independently
2. Verify Playwright tests run independently
3. Confirm no cross-contamination