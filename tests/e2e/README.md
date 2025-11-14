# End-to-End Journey Testing

Comprehensive user journey validation using Playwright to ensure marketing, documentation, and functionality align.

## Purpose

These tests validate that the actual user experience matches what we promise across all touchpoints:
- Marketing claims match implemented features
- Documentation examples work as written
- Pricing reflects enforced billing limits
- User flows complete successfully
- Performance meets expectations

## Test Structure

```
tests/e2e/
├── journeys/              # User journey test suites
│   ├── developer-integrator.spec.ts
│   ├── end-user.spec.ts
│   ├── security-admin.spec.ts
│   └── business-decision-maker.spec.ts
├── fixtures/              # Test data and personas
│   ├── personas.ts
│   ├── test-data.ts
│   └── api-clients.ts
├── helpers/               # Validation and utility functions
│   ├── content-validator.ts
│   ├── journey-metrics.ts
│   ├── feature-validator.ts
│   └── performance-tracker.ts
├── pages/                 # Page object models
│   ├── landing.page.ts
│   ├── signup.page.ts
│   ├── dashboard.page.ts
│   └── admin.page.ts
└── config/                # Test configuration
    ├── environments.ts
    └── test-accounts.ts
```

## Running Tests

### Local Development

```bash
# Start local test environment
npm run test:journeys:setup

# Run all journey tests
npm run test:journeys

# Run specific persona journey
npx playwright test tests/e2e/journeys/developer-integrator.spec.ts

# Run with UI for debugging
npx playwright test --headed --debug

# Run specific test
npx playwright test -g "Signup: Complete account creation"

# Cleanup
npm run test:journeys:teardown
```

### CI/CD Pipeline

```bash
# Run in GitHub Actions
npm run test:journeys:ci

# Generate HTML report
npx playwright show-report
```

## Test Categories

### Content-Functionality Alignment
Validates marketing claims match code reality:
- Features claimed on landing page exist in codebase
- Pricing tiers match billing service enforcement
- Documentation examples compile and run successfully
- Performance claims verified with actual measurements

### User Journey Completeness
Validates complete user flows work end-to-end:
- Signup → verification → first login
- Integration → testing → production deployment
- Security configuration → monitoring → incident response
- Evaluation → trial → purchase decision

### Cross-Touchpoint Consistency
Validates consistent experience across all touchpoints:
- Landing page promises match documentation
- Documentation reflects actual SDK behavior
- Admin interface enforces documented policies
- Support resources address real user needs

## Writing New Tests

### Page Object Pattern

```typescript
// tests/e2e/pages/signup.page.ts
export class SignupPage {
  constructor(private page: Page) {}

  async navigateTo() {
    await this.page.goto('http://localhost:3000/signup');
  }

  async fillSignupForm(email: string, password: string, name: string) {
    await this.page.fill('[data-testid="signup-email"]', email);
    await this.page.fill('[data-testid="signup-password"]', password);
    await this.page.fill('[data-testid="signup-name"]', name);
  }

  async submitSignup() {
    await this.page.click('[data-testid="signup-submit"]');
  }

  async assertSignupSuccess() {
    await expect(this.page.locator('[data-testid="signup-success"]')).toBeVisible();
  }
}
```

### Using Fixtures

```typescript
// tests/e2e/journeys/example.spec.ts
import { test } from '@playwright/test';
import { DeveloperPersona } from '../fixtures/personas';
import { SignupPage } from '../pages/signup.page';

test('Developer signup flow', async ({ page }) => {
  const persona = DeveloperPersona.create();
  const signupPage = new SignupPage(page);

  await signupPage.navigateTo();
  await signupPage.fillSignupForm(persona.email, persona.password, persona.name);
  await signupPage.submitSignup();
  await signupPage.assertSignupSuccess();
});
```

## Test Data Management

### Persona Factory

```typescript
// tests/e2e/fixtures/personas.ts
export class DeveloperPersona {
  static create() {
    return {
      email: `dev-${Date.now()}@example.com`,
      password: 'SecureDevP@ss123',
      name: 'Test Developer',
      role: 'developer',
      company: 'Acme Corp'
    };
  }
}
```

### Test Data Cleanup

Tests should clean up after themselves:

```typescript
test.afterEach(async ({ page, request }) => {
  // Delete test user
  await request.delete(`/api/users/${testUserId}`);
  
  // Clear test sessions
  await request.post('/api/sessions/clear-test');
});
```

## Performance Tracking

Track journey performance metrics:

```typescript
import { JourneyMetrics } from '../helpers/journey-metrics';

test('Signup performance meets expectations', async ({ page }) => {
  const metrics = new JourneyMetrics();
  
  metrics.startJourney('developer-signup');
  
  await page.goto('http://localhost:3000/signup');
  metrics.checkpoint('page-load');
  
  await page.fill('[data-testid="email"]', 'test@example.com');
  await page.click('[data-testid="signup-submit"]');
  metrics.checkpoint('form-submit');
  
  await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
  metrics.checkpoint('dashboard-load');
  
  metrics.endJourney(true);
  
  // Validate marketing claim "<30 seconds to signup"
  expect(metrics.totalTime()).toBeLessThan(30000);
});
```

## Content Validation

Validate marketing claims match code:

```typescript
import { ContentValidator } from '../helpers/content-validator';

test('Features page claims match implementations', async ({ page }) => {
  await page.goto('http://localhost:3000/features');
  
  // Get all claimed features
  const features = await page.locator('[data-testid="feature"]').allTextContents();
  
  // Validate each feature has implementation
  for (const feature of features) {
    const hasImplementation = await ContentValidator.validateFeatureClaim(
      feature,
      'apps/api/' // Search codebase for implementation
    );
    
    expect(hasImplementation).toBeTruthy(
      `Feature "${feature}" claimed but not implemented`
    );
  }
});
```

## Debugging Tests

### Visual Debugging

```bash
# Run with headed browser
npx playwright test --headed

# Run with debug mode (step through)
npx playwright test --debug

# Run specific test with debug
npx playwright test -g "specific test name" --debug
```

### Screenshots and Videos

```typescript
test('Capture evidence of failure', async ({ page }) => {
  await page.goto('http://localhost:3000');
  
  // Take screenshot
  await page.screenshot({ path: 'test-evidence/homepage.png' });
  
  // Test assertions...
  
  // On failure, video is automatically saved (if configured)
});
```

## Test Maintenance

### Keep Tests Up-to-Date
- Update tests when features change
- Validate test data remains realistic
- Review and remove obsolete tests
- Update page objects when UI changes

### Test Reliability
- Use stable selectors (`data-testid` attributes)
- Add appropriate wait conditions
- Handle async operations properly
- Avoid flaky assertions

## Related Documentation

- [User Journey Maps](../../docs/user-journeys/)
- [Playwright Configuration](../../playwright.config.ts)
- [Content Validation Guide](../helpers/content-validator.ts)
- [CI/CD Integration](.github/workflows/validate-journeys.yml)
