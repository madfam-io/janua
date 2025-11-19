# Backup Codes Component - Test Suite Guide

Quick reference for understanding and maintaining the backup-codes test suite.

## Quick Stats

- **Tests**: 39 total (100% passing)
- **Coverage**: 100% statements, 93% branches, 100% functions
- **Runtime**: ~4.3 seconds
- **File**: `backup-codes.test.tsx`

## Running Tests

```bash
# Run all backup-codes tests
npm test -- backup-codes.test.tsx

# Run with coverage
npm test -- backup-codes.test.tsx --coverage

# Run specific test
npm test -- backup-codes.test.tsx -t "should copy code to clipboard"

# Watch mode
npm test -- backup-codes.test.tsx --watch
```

## Test Categories

### 1. Rendering (6 tests)
Tests component mounting, loading states, and conditional rendering.

### 2. Code Display (5 tests)
Tests code presentation, styling, and button visibility.

### 3. Copy Functionality (3 tests)
Tests clipboard operations, success states, and error handling.

### 4. Download Functionality (4 tests)
Tests download trigger, content generation, and conditional sections.

### 5. Regenerate Functionality (9 tests)
Tests confirmation flow, cancellation, success/error states.

### 6. Warning Messages (4 tests)
Tests low code warnings and conditional display logic.

### 7. Information Section (1 test)
Tests static content display.

### 8. Accessibility (3 tests)
Tests ARIA labels, keyboard navigation, and screen reader support.

### 9. Error Handling (2 tests)
Tests error display and error clearing logic.

## Common Patterns

### Async Element Queries
```typescript
// Wait for element to appear
const button = await screen.findByRole('button', { name: /confirm/i })

// Wait for state change
await waitFor(() => {
  expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
})
```

### User Interactions
```typescript
const user = userEvent.setup()
await user.click(button)
await user.type(input, 'text')
```

### Mock Setup
```typescript
// Mock functions are reset in beforeEach
mockOnFetchCodes.mockResolvedValue(mockBackupCodes)

// Clipboard mocking
Object.defineProperty(navigator, 'clipboard', {
  value: { writeText: vi.fn(), readText: vi.fn() },
  configurable: true,
})
```

## Troubleshooting

### Test Passes Individually But Fails in Suite
- **Cause**: Test isolation issue, shared state between tests
- **Solution**: Check that cleanup() is running in afterEach
- **Check**: Verify all mocks are being reset in beforeEach

### Timeout Errors
- **Cause**: Missing cleanup of timers or async operations
- **Solution**: Add vi.clearAllTimers() to afterEach
- **Check**: Look for setTimeout/setInterval in component

### Mock Not Working
- **Cause**: Mock setup order, render timing
- **Solution**: For DOM mocks, render component first
- **Check**: Verify mock is applied before user action

### Clipboard Tests Failing
- **Cause**: Mock not being applied correctly
- **Solution**: Redefine entire navigator.clipboard object
- **Pattern**: See "should handle clipboard errors gracefully" test

## Maintenance Checklist

When modifying tests:
- [ ] Run full suite to verify no regressions
- [ ] Check coverage hasn't decreased
- [ ] Verify test passes individually AND in suite
- [ ] Update this guide if adding new patterns
- [ ] Add comments for complex mocking scenarios

## Known Issues

### JSDOM Warning
**Message**: `Not implemented: navigation to another Document`
**Impact**: None - cosmetic only
**Context**: Appears during download tests
**Action**: Safe to ignore - JSDOM limitation

## Coverage Analysis

### What's Tested
- ✅ All component props and variations
- ✅ User interactions (click, type, keyboard nav)
- ✅ Async operations (fetch, regenerate)
- ✅ Error scenarios (network, clipboard, validation)
- ✅ Edge cases (empty states, boundary conditions)
- ✅ Accessibility (ARIA, keyboard, labels)

### What's Not Tested
- Visual appearance (consider visual regression tests)
- Performance under load (consider performance tests)
- Real browser behavior (consider E2E tests)

## Best Practices

1. **Use semantic queries**: Prefer `getByRole` over `getByTestId`
2. **Wait for async**: Use `findBy` or `waitFor` for async elements
3. **Clean mocks**: Reset in beforeEach, restore in afterEach
4. **Real timers**: Prefer real timers over fake timers when possible
5. **Descriptive names**: Test names should describe behavior, not implementation

## Quick Reference

### Mock Data
```typescript
const mockBackupCodes = [
  { code: 'CODE1234', used: false },
  { code: 'CODE5678', used: false },
  { code: 'CODE9012', used: true },
  // ...
]
```

### Common Assertions
```typescript
// Element presence
expect(screen.getByText('text')).toBeInTheDocument()
expect(screen.queryByText('text')).not.toBeInTheDocument()

// Mock calls
expect(mockFn).toHaveBeenCalled()
expect(mockFn).toHaveBeenCalledWith('arg')

// Content checks
expect(element).toHaveTextContent('text')
expect(element).toHaveClass('className')
```

## Resources

- [Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [Vitest Docs](https://vitest.dev/)
- [Full Implementation Report](../../../docs/implementation-reports/backup-codes-test-suite-completion.md)

---

Last Updated: November 17, 2025
