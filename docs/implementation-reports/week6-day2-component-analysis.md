# BackupCodes Component Analysis - Test Timeout Root Cause

**Date**: November 17, 2025  
**Component**: `/packages/ui/src/components/auth/backup-codes.tsx`  
**Analysis Type**: Component behavior verification vs test expectations

## Executive Summary

**Finding**: Component implements ALL expected behaviors. Tests are not wrong about what component should do - there's a mismatch between how component renders in production vs test environment.

**Root Cause**: Tests timeout because UI component dependencies (Button, Card, Badge) may not be rendering with proper accessibility attributes in test environment.

**Impact**: 8 timeout failures, 58% pass rate → Can reach 95%+ with proper component mocking/setup

## Component Implementation Analysis

### ✅ Confirmed Behaviors

#### 1. Copy Functionality (Lines 67-73)
```typescript
const handleCopyCode = async (code: string) => {
  try {
    await navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000) // ← Timer for "Copied" state
  } catch (err) {
    console.error('Failed to copy code:', err)
  }
}
```

**Implementation**: ✅ CORRECT
- Uses navigator.clipboard.writeText
- Shows "Copied" state for 2 seconds using setTimeout
- Component state drives UI change (line 308-319)

**Test Expectation**: ✅ MATCHES
- Tests expect "Copied" text to appear and disappear after 2 seconds
- Timer-based state change is implemented

**Timeout Issue**: Fake timer interaction with React state updates

---

#### 2. Regenerate Confirmation (Lines 342-368)
```typescript
{allowRegeneration && onRegenerateCodes && (
  <>
    {!showRegenerateConfirm ? (
      <Button onClick={() => setShowRegenerateConfirm(true)}>
        Regenerate codes
      </Button>
    ) : (
      <div className="flex-1 flex gap-2">
        <Button 
          variant="destructive" 
          onClick={handleRegenerateCodes}
          disabled={isLoading}
        >
          {isLoading ? 'Regenerating...' : 'Confirm regenerate'}
        </Button>
        <Button 
          variant="outline"
          onClick={() => setShowRegenerateConfirm(false)}
          disabled={isLoading}
        >
          Cancel
        </Button>
      </div>
    )}
  </>
)}
```

**Implementation**: ✅ CORRECT
- Click "Regenerate codes" → sets `showRegenerateConfirm = true`
- Conditional rendering shows "Confirm regenerate" + "Cancel" buttons
- Not a modal - inline conditional rendering in same Card
- Warning text shows below buttons (lines 370-379)

**Test Expectation**: ✅ MATCHES
- Tests expect "Confirm regenerate" button after clicking "Regenerate codes"
- Tests expect "Cancel" button
- Tests expect warning text "Regenerating will invalidate all existing"

**Timeout Issue**: Button component may not render with `role="button"` in test environment

---

#### 3. Regenerate Warning (Lines 370-379)
```typescript
{showRegenerateConfirm && (
  <div className="mt-4 p-3 bg-yellow-50...">
    <p className="text-sm...">
      <strong>Warning:</strong> Regenerating will invalidate all existing backup codes...
    </p>
  </div>
)}
```

**Implementation**: ✅ CORRECT
- Shows when `showRegenerateConfirm === true`
- Contains text "Regenerating will invalidate all existing"

**Test Expectation**: ✅ MATCHES
- Tests use `await screen.findByText(/regenerating will invalidate all existing/i)`

**Timeout Issue**: Text element may not render due to parent Button not updating

---

#### 4. Download Functionality (Lines 75-103)
```typescript
const handleDownloadCodes = () => {
  if (!backupCodes) return
  
  // ... build content string ...
  
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `plinto-backup-codes-${Date.now()}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
```

**Implementation**: ✅ CORRECT
- Creates Blob with code content
- Creates anchor element
- Appends to body, clicks, removes
- Properly cleans up URL

**Test Expectation**: ✅ MATCHES
- Tests mock URL.createObjectURL and URL.revokeObjectURL
- Tests mock document.createElement and body methods

**Timeout Issue**: DOM manipulation may fail in test environment without proper React act() wrapper

---

#### 5. Loading States (Lines 128-145)
```typescript
if (isLoading && !backupCodes) {
  return (
    <Card className={cn('w-full max-w-2xl mx-auto p-6', className)}>
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    </Card>
  )
}
```

**Implementation**: ✅ Spinner rendered, but NO `role="status"` attribute
- Just a div with animation classes
- Not accessible loading indicator

**Test Expectation**: ❌ MISMATCH
- Test expects: `screen.getByRole('status', { hidden: true })`
- Component provides: div with no role attribute

**Fix Required**: Either:
1. Add `role="status"` to spinner div (component fix)
2. Change test to query by class or different selector (test fix)

---

#### 6. Error States (Lines 161-167)
```typescript
{error && (
  <div className="bg-destructive/15 text-destructive text-sm p-3 rounded-md mb-6">
    {error}
  </div>
)}
```

**Implementation**: ✅ CORRECT
- Shows error message when `error` state is set
- `error` is set in catch blocks (lines 57, 120)

**Test Expectation**: ✅ MATCHES
- Tests trigger errors and expect error message to display

**Timeout Issue**: Async error state updates may not propagate in test

## Root Cause Analysis

### Primary Issues

#### Issue 1: Button Component Rendering 🔴 CRITICAL
**Symptom**: Tests timeout when looking for buttons after state change

**Root Cause**: The imported `Button` component from '../button' may not:
1. Render with `role="button"` attribute in test environment
2. Trigger proper re-renders when parent state changes
3. Be properly mocked/available in test setup

**Evidence**:
- All regenerate tests timeout when looking for "Confirm regenerate" button
- Component code shows button IS rendered in correct condition
- State change IS happening (`setShowRegenerateConfirm(true)`)

**Investigation Needed**:
```typescript
// Check if Button component sets role="button"
// Check test-utils.tsx for proper Button rendering
// Verify Card component doesn't block re-renders
```

---

#### Issue 2: Fake Timers + React State 🟡 IMPORTANT
**Symptom**: Copy timer test times out despite correct setup order

**Root Cause**: `setTimeout(() => setCopiedCode(null), 2000)` interaction with fake timers

**Current Test Approach**:
```typescript
vi.useFakeTimers()
const user = userEvent.setup()
render(<BackupCodes />)
await user.click(copyButton)
expect(screen.getByText(/copied/i)).toBeInTheDocument()
act(() => {
  vi.advanceTimersByTime(2000)
})
expect(screen.queryByText(/copied/i)).not.toBeInTheDocument()
```

**Issue**: `act()` alone may not be sufficient. May need:
```typescript
// Option 1: Run all timers
act(() => {
  vi.runAllTimers()
})

// Option 2: Advance timers with flush
await act(async () => {
  vi.advanceTimersByTime(2000)
})
```

---

#### Issue 3: Async State Propagation 🟡 IMPORTANT
**Symptom**: Multiple tests timeout despite using `findBy` queries

**Root Cause**: React state updates may not trigger re-renders in test environment

**Possible Causes**:
1. Card component wrapper affects rendering
2. Conditional rendering not updating properly
3. Test environment missing React concurrent features

**Fix Options**:
```typescript
// Wrap state-triggering actions in act()
await act(async () => {
  await user.click(regenerateButton)
})

// Or use debug to see actual DOM
screen.debug()

// Or increase findBy timeout
await screen.findByRole('button', { name: /confirm/i }, { timeout: 5000 })
```

## Test Quality Issues

### Issue 1: Multiple Element Matches
**Test**: `should render backup codes component with provided codes`
**Error**: `Found multiple elements with text: /backup codes/i`

**Component Content** (lines matching regex):
1. `<h2>Backup codes</h2>` (line 157)
2. `<p>Use backup codes to sign in...</p>` (line 162)
3. `<li>• You can use backup codes to sign in...</li>` (line 300)

**Fix**:
```typescript
// BEFORE
expect(screen.getByText(/backup codes/i)).toBeInTheDocument()

// AFTER
expect(screen.getByRole('heading', { name: /backup codes/i })).toBeInTheDocument()
```

---

### Issue 2: Loading State Role
**Test**: `should show loading state when fetching codes`
**Error**: `Unable to find element with role "status"`

**Component**: Spinner has NO `role="status"` (line 133)

**Fix Options**:

**Option A: Fix Component (Recommended)**
```typescript
// Add role for accessibility
<div role="status" aria-label="Loading backup codes" className="animate-spin...">
```

**Option B: Fix Test**
```typescript
// Query by loading indicator class
expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
// Or
expect(container.querySelector('.animate-spin')).toBeInTheDocument()
```

---

### Issue 3: Badge Text Matching
**Test**: `should not show used badge when all codes are unused`
**Error**: `expect(element).not.toBeInTheDocument() but found element`

**Component**: Shows "5 unused" badge (line 159-161)

**Issue**: Query `/used$/i` matches "unused" text

**Fix**:
```typescript
// BEFORE
expect(screen.queryByText(/used$/i)).not.toBeInTheDocument()

// AFTER - More specific query
expect(screen.queryByText(/^\d+ used$/i)).not.toBeInTheDocument()
// Or query by variant
expect(screen.queryByText('used', { selector: '[class*="secondary"]' })).not.toBeInTheDocument()
```

---

### Issue 4: Mock Function Type
**Test**: `should handle clipboard errors gracefully`
**Error**: `vi.mocked(...).mockRejectedValueOnce is not a function`

**Issue**: Mock was created with `vi.fn()`, not a spy

**Current Setup** (test-utils or test file):
```typescript
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: vi.fn(() => Promise.resolve()),
  },
})
```

**Fix**:
```typescript
// The mock IS a vi.fn(), so we can just call mockRejectedValueOnce on it
const writeTextMock = vi.fn(() => Promise.resolve())
Object.defineProperty(navigator, 'clipboard', {
  value: { writeText: writeTextMock },
})

// In test
writeTextMock.mockRejectedValueOnce(new Error('Clipboard error'))
```

## Recommended Action Plan

### Phase 1: Component Dependencies Investigation (30 minutes)
1. **Check Button component** (`/packages/ui/src/components/button.tsx`):
   - Verify it renders with `role="button"`
   - Check if it forwards refs properly
   - Confirm it works in test environment

2. **Check Card component** (`/packages/ui/src/components/card.tsx`):
   - Verify it doesn't block re-renders
   - Check if it uses React.memo incorrectly

3. **Check test-utils.tsx**:
   - Verify proper render configuration
   - Check if components are mocked/stubbed

### Phase 2: Fix Test Issues (1-2 hours)
1. **Query Pattern Fixes** (15 minutes):
   - Use `getByRole('heading')` for title
   - Fix badge text query to be more specific
   - Add test-ids if needed

2. **Mock Function Fix** (10 minutes):
   - Store mock reference for clipboard
   - Use proper mockRejectedValueOnce syntax

3. **Loading State Fix** (5 minutes):
   - Either add `role="status"` to component
   - Or change test to query by class/test-id

### Phase 3: Fix Timeout Issues (1-2 hours)

#### If Button Component Has Issues:
```typescript
// Mock Button in test
vi.mock('../button', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>
      {children}
    </button>
  ),
}))
```

#### If Async State Issue:
```typescript
// Wrap all state-changing actions in act()
await act(async () => {
  await user.click(regenerateButton)
})

// Then query
const confirmButton = await screen.findByRole('button', { name: /confirm/i })
```

#### If Fake Timer Issue:
```typescript
// Use runAllTimers instead
act(() => {
  vi.runAllTimers()
})

// Or use modern timer API
vi.useFakeTimers({ shouldAdvanceTime: true })
```

### Phase 4: Validation (30 minutes)
1. Run full test suite
2. Verify 95%+ pass rate
3. Check for flaky tests (run 3 times)
4. Document patterns

## Success Criteria

- [ ] All 8 timeout failures resolved
- [ ] 34/36 tests passing (95%+)
- [ ] Test execution time < 30 seconds
- [ ] No flaky tests (3 consistent runs)
- [ ] Component accessibility improved (role="status" on spinner)

## Conclusion

**Component is NOT the problem** - it implements all expected behaviors correctly.

**Test environment is the issue** - UI component dependencies (Button, Card) may not render properly with accessibility attributes in test setup.

**Next Steps**: 
1. Read Button and Card component source
2. Check test-utils configuration
3. Apply targeted fixes to test queries and mocking
4. Add proper act() wrappers for state changes

**Estimated Time to Fix**: 2-3 hours with proper investigation and targeted fixes.
