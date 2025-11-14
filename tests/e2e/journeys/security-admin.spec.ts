import { test, expect } from '@playwright/test';
import { SecurityAdminPersona } from '../fixtures/personas';
import { JourneyMetricsTracker } from '../helpers/journey-metrics';

test.describe('Security Admin Journey', () => {
  let metrics: JourneyMetricsTracker;

  test.beforeEach(() => {
    metrics = new JourneyMetricsTracker();
  });

  test.afterEach(async () => {
    const result = metrics.endJourney(true);
    console.log('Security Admin Journey metrics:', result);
  });

  test('Stage 1: Security Evaluation - Feature Assessment', async ({ page }) => {
    metrics.startJourney('security-admin-evaluation');

    // Navigate to landing page
    await page.goto('http://localhost:3001');
    metrics.checkpoint('landing-page');

    // Verify security features are highlighted
    await expect(page.getByTestId('feature-mfa')).toBeVisible();
    await expect(page.getByTestId('feature-passkey')).toBeVisible();
    await expect(page.getByTestId('feature-security')).toBeVisible();

    // Check for security-related content
    const mfaFeature = page.getByTestId('feature-mfa');
    await expect(mfaFeature).toContainText('MFA');

    const passkeyFeature = page.getByTestId('feature-passkey');
    await expect(passkeyFeature).toContainText('Passkey');

    metrics.checkpoint('security-features-verified');
  });

  test('Stage 2: Account Security Testing', async ({ page }) => {
    metrics.startJourney('security-admin-account-testing');

    const persona = SecurityAdminPersona.createOrgAdmin();

    // Create test account
    await page.goto('http://localhost:3001/signup');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('account-created');

    // Access security settings
    await page.getByTestId('security-link').click();
    await page.waitForURL('**/security');
    metrics.checkpoint('security-settings-accessed');

    // Verify all security options are available
    await expect(page.getByTestId('mfa-section')).toBeVisible();
    await expect(page.getByTestId('password-section')).toBeVisible();
    await expect(page.getByTestId('passkey-section')).toBeVisible();

    metrics.checkpoint('security-options-verified');
  });

  test('Stage 3: MFA Configuration Testing', async ({ page }) => {
    metrics.startJourney('security-admin-mfa-testing');

    const persona = SecurityAdminPersona.createSecurityOfficer();

    // Setup account
    await page.goto('http://localhost:3001/signup');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');

    // Navigate to security
    await page.getByTestId('security-link').click();
    await page.waitForURL('**/security');
    metrics.checkpoint('security-page-loaded');

    // Enable MFA
    await page.getByTestId('enable-mfa-button').click();
    await page.waitForSelector('[data-testid="mfa-setup"]', { timeout: 10000 });
    metrics.checkpoint('mfa-enabled');

    // Verify MFA setup components
    await expect(page.getByTestId('mfa-qr-code')).toBeVisible();
    await expect(page.getByTestId('backup-codes')).toBeVisible();
    await expect(page.getByTestId('mfa-code-input')).toBeVisible();
    await expect(page.getByTestId('verify-mfa-button')).toBeVisible();

    // Verify backup codes count
    const backupCodes = page.locator('[data-testid="backup-codes"] li');
    const count = await backupCodes.count();
    expect(count).toBeGreaterThan(0);

    metrics.checkpoint('mfa-configuration-verified');
  });

  test('Stage 4: Password Policy Validation', async ({ page }) => {
    metrics.startJourney('security-admin-password-policy');

    const persona = SecurityAdminPersona.createComplianceOfficer();

    // Create account
    await page.goto('http://localhost:3001/signup');
    metrics.checkpoint('signup-page-loaded');

    // Test weak password rejection (if implemented)
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);

    // Try weak password
    await page.getByTestId('password-input').fill('weak');

    // Check minimum length requirement (HTML5 validation)
    const passwordInput = page.getByTestId('password-input');
    const minLength = await passwordInput.getAttribute('minlength');
    expect(minLength).toBe('8');

    // Use strong password
    await page.getByTestId('password-input').clear();
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('strong-password-accepted');

    // Test password change with validation
    await page.getByTestId('security-link').click();
    await page.waitForURL('**/security');

    // Verify password change form has validation
    const newPasswordInput = page.getByTestId('new-password-input');
    const newMinLength = await newPasswordInput.getAttribute('minlength');
    expect(newMinLength).toBe('8');

    metrics.checkpoint('password-policy-verified');
  });

  test('Stage 5: Session Management Testing', async ({ page }) => {
    metrics.startJourney('security-admin-session-management');

    const persona = SecurityAdminPersona.createOrgAdmin();

    // Create and login
    await page.goto('http://localhost:3001/signup');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('logged-in');

    // Verify session exists (cookies)
    const cookies = await page.context().cookies();
    const accessToken = cookies.find(c => c.name === 'access_token');
    const refreshToken = cookies.find(c => c.name === 'refresh_token');
    const user = cookies.find(c => c.name === 'user');

    expect(accessToken).toBeDefined();
    expect(refreshToken).toBeDefined();
    expect(user).toBeDefined();
    metrics.checkpoint('session-cookies-verified');

    // Test logout clears session
    await page.getByTestId('logout-button').click();
    await page.waitForURL('**/');

    // Verify cookies cleared
    const cookiesAfterLogout = await page.context().cookies();
    const accessTokenAfter = cookiesAfterLogout.find(c => c.name === 'access_token');
    const refreshTokenAfter = cookiesAfterLogout.find(c => c.name === 'refresh_token');

    expect(accessTokenAfter).toBeUndefined();
    expect(refreshTokenAfter).toBeUndefined();
    metrics.checkpoint('session-cleared');
  });

  test('Stage 6: Protected Route Access Control', async ({ page }) => {
    metrics.startJourney('security-admin-access-control');

    // Try to access protected routes without authentication
    const protectedRoutes = ['/dashboard', '/profile', '/security', '/passkey/register'];

    for (const route of protectedRoutes) {
      await page.goto(`http://localhost:3001${route}`);
      await page.waitForURL('**/login', { timeout: 5000 });

      // Should redirect to login
      await expect(page.getByTestId('login-title')).toBeVisible();
      metrics.checkpoint(`protected-route-${route}-blocked`);
    }

    // Create account and verify access is granted
    await page.goto('http://localhost:3001/signup');
    const persona = SecurityAdminPersona.createOrgAdmin();
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('authenticated');

    // Now should be able to access protected routes
    for (const route of ['/profile', '/security']) {
      await page.goto(`http://localhost:3001${route}`);

      // Should not redirect to login
      expect(page.url()).toContain(route);
      metrics.checkpoint(`protected-route-${route}-accessible`);
    }
  });

  test('Stage 7: Security Monitoring - Error Handling', async ({ page }) => {
    metrics.startJourney('security-admin-error-handling');

    // Test login with invalid credentials
    await page.goto('http://localhost:3001/login');
    await page.getByTestId('email-input').fill('nonexistent@example.com');
    await page.getByTestId('password-input').fill('WrongPassword123!');
    await page.getByTestId('login-submit').click();
    metrics.checkpoint('invalid-login-attempted');

    // Should show error message
    await expect(page.getByTestId('error-message')).toBeVisible();
    await expect(page.getByTestId('error-message')).toContainText(/login failed|invalid|not found/i);

    // Verify still on login page
    await expect(page.getByTestId('login-title')).toBeVisible();
    metrics.checkpoint('error-displayed');
  });

  test('Complete Security Admin Journey', async ({ page }) => {
    metrics.startJourney('security-admin-complete');

    const persona = SecurityAdminPersona.createSecurityOfficer();

    // 1. Security Feature Evaluation
    await page.goto('http://localhost:3001');
    await expect(page.getByTestId('feature-mfa')).toBeVisible();
    await expect(page.getByTestId('feature-passkey')).toBeVisible();
    await expect(page.getByTestId('feature-security')).toBeVisible();
    metrics.checkpoint('features-evaluated');

    // 2. Create Test Account
    await page.getByTestId('signup-button').click();
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('account-created');

    // 3. Configure MFA
    await page.getByTestId('security-link').click();
    await page.waitForURL('**/security');
    await page.getByTestId('enable-mfa-button').click();
    await page.waitForSelector('[data-testid="mfa-setup"]');
    await expect(page.getByTestId('mfa-qr-code')).toBeVisible();
    metrics.checkpoint('mfa-configured');

    // 4. Test Password Change
    await page.getByTestId('current-password-input').fill(persona.password);
    await page.getByTestId('new-password-input').fill('NewSecurePass123!');
    await page.getByTestId('change-password-button').click();
    await page.waitForSelector('[data-testid="success-message"]');
    metrics.checkpoint('password-changed');

    // 5. Verify Security Status
    await page.getByTestId('dashboard-link').click();
    await page.waitForURL('**/dashboard');
    await expect(page.getByTestId('security-status-card')).toBeVisible();
    metrics.checkpoint('security-status-verified');

    // 6. Test Logout
    await page.getByTestId('logout-button').click();
    await page.waitForURL('**/');
    metrics.checkpoint('logout-verified');

    // 7. Verify Protected Route Access
    await page.goto('http://localhost:3001/dashboard');
    await page.waitForURL('**/login');
    await expect(page.getByTestId('login-title')).toBeVisible();
    metrics.checkpoint('access-control-verified');
  });
});
