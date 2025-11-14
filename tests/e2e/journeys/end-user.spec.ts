import { test, expect } from '@playwright/test';
import { EndUserPersona } from '../fixtures/personas';
import { JourneyMetricsTracker, PerformanceExpectations } from '../helpers/journey-metrics';

test.describe('End User Journey', () => {
  let metrics: JourneyMetricsTracker;

  test.beforeEach(() => {
    metrics = new JourneyMetricsTracker();
  });

  test.afterEach(async () => {
    const result = metrics.endJourney(true);
    const validation = PerformanceExpectations.validate(result);
    console.log('Journey metrics:', result);
    console.log('Performance validation:', validation);
  });

  test('Stage 1: Complete Signup Flow', async ({ page }) => {
    metrics.startJourney('end-user-signup');
    const persona = EndUserPersona.create();

    // Navigate to test app
    await page.goto('http://localhost:3001');
    metrics.checkpoint('landing-page-load');

    // Verify landing page
    await expect(page.getByTestId('hero-section')).toBeVisible();
    await expect(page.getByTestId('signup-button')).toBeVisible();

    // Click signup button
    await page.getByTestId('signup-button').click();
    await page.waitForURL('**/signup');
    metrics.checkpoint('signup-page-load');

    // Fill signup form
    await expect(page.getByTestId('signup-title')).toHaveText('Sign Up');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    metrics.checkpoint('signup-form-filled');

    // Submit signup
    await page.getByTestId('signup-submit').click();

    // Should redirect to dashboard
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    metrics.checkpoint('signup-complete');

    // Verify dashboard
    await expect(page.getByTestId('dashboard')).toBeVisible();
    await expect(page.getByTestId('user-email')).toHaveText(persona.email);
    await expect(page.getByTestId('user-name')).toHaveText(persona.name);
  });

  test('Stage 2: Login Flow', async ({ page }) => {
    metrics.startJourney('end-user-login');

    // First create an account
    const persona = EndUserPersona.create();
    await page.goto('http://localhost:3001/signup');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');

    // Logout
    await page.getByTestId('logout-button').click();
    await page.waitForURL('**/', { timeout: 5000 });
    metrics.checkpoint('logged-out');

    // Navigate to login
    await page.goto('http://localhost:3001/login');
    metrics.checkpoint('login-page-load');

    // Fill login form
    await expect(page.getByTestId('login-title')).toHaveText('Login');
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    metrics.checkpoint('login-form-filled');

    // Submit login
    await page.getByTestId('login-submit').click();

    // Should redirect to dashboard
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    metrics.checkpoint('login-complete');

    // Verify dashboard
    await expect(page.getByTestId('dashboard')).toBeVisible();
    await expect(page.getByTestId('user-email')).toHaveText(persona.email);
  });

  test('Stage 3: Profile Management', async ({ page }) => {
    metrics.startJourney('end-user-profile');

    // Create account and login
    const persona = EndUserPersona.create();
    await page.goto('http://localhost:3001/signup');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('logged-in');

    // Navigate to profile
    await page.getByTestId('profile-link').click();
    await page.waitForURL('**/profile');
    metrics.checkpoint('profile-page-load');

    // Verify profile form
    await expect(page.getByTestId('profile-title')).toHaveText('Profile Settings');
    await expect(page.getByTestId('name-input')).toHaveValue(persona.name);
    await expect(page.getByTestId('email-input')).toHaveValue(persona.email);

    // Update profile
    const newName = 'Updated Name';
    await page.getByTestId('name-input').clear();
    await page.getByTestId('name-input').fill(newName);
    metrics.checkpoint('profile-updated');

    // Submit update
    await page.getByTestId('update-profile-button').click();
    await page.waitForSelector('[data-testid="success-message"]', { timeout: 5000 });
    metrics.checkpoint('profile-save-complete');

    // Verify success message
    await expect(page.getByTestId('success-message')).toBeVisible();
    await expect(page.getByTestId('success-message')).toContainText('Profile updated successfully');

    // Verify name was updated
    await expect(page.getByTestId('name-input')).toHaveValue(newName);
  });

  test('Stage 4: MFA Setup', async ({ page }) => {
    metrics.startJourney('end-user-mfa-setup');

    // Create account and login
    const persona = EndUserPersona.create();
    await page.goto('http://localhost:3001/signup');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('logged-in');

    // Navigate to security settings
    await page.getByTestId('security-link').click();
    await page.waitForURL('**/security');
    metrics.checkpoint('security-page-load');

    // Verify security page
    await expect(page.getByTestId('security-title')).toHaveText('Security Settings');
    await expect(page.getByTestId('mfa-section')).toBeVisible();

    // Enable MFA
    await page.getByTestId('enable-mfa-button').click();
    await page.waitForSelector('[data-testid="mfa-setup"]', { timeout: 10000 });
    metrics.checkpoint('mfa-enabled');

    // Verify MFA setup elements
    await expect(page.getByTestId('mfa-setup')).toBeVisible();
    await expect(page.getByTestId('mfa-qr-code')).toBeVisible();
    await expect(page.getByTestId('backup-codes')).toBeVisible();

    // Verify backup codes exist
    const backupCodes = page.locator('[data-testid="backup-codes"] li');
    await expect(backupCodes).toHaveCount(10); // Assuming 10 backup codes

    // Note: Actual MFA verification would require TOTP code generation
    // For testing purposes, this validates the UI flow
    metrics.checkpoint('mfa-setup-complete');
  });

  test('Stage 5: Password Change', async ({ page }) => {
    metrics.startJourney('end-user-password-change');

    // Create account and login
    const persona = EndUserPersona.create();
    await page.goto('http://localhost:3001/signup');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('logged-in');

    // Navigate to security settings
    await page.getByTestId('security-link').click();
    await page.waitForURL('**/security');
    metrics.checkpoint('security-page-load');

    // Find password section
    await expect(page.getByTestId('password-section')).toBeVisible();

    // Fill password change form
    const newPassword = 'NewSecurePass123!';
    await page.getByTestId('current-password-input').fill(persona.password);
    await page.getByTestId('new-password-input').fill(newPassword);
    metrics.checkpoint('password-form-filled');

    // Submit password change
    await page.getByTestId('change-password-button').click();
    await page.waitForSelector('[data-testid="success-message"]', { timeout: 10000 });
    metrics.checkpoint('password-changed');

    // Verify success
    await expect(page.getByTestId('success-message')).toBeVisible();
    await expect(page.getByTestId('success-message')).toContainText('Password changed successfully');

    // Logout and login with new password
    await page.getByTestId('logout-button').click();
    await page.waitForURL('**/');

    await page.goto('http://localhost:3001/login');
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(newPassword);
    await page.getByTestId('login-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('login-with-new-password');

    // Verify successful login
    await expect(page.getByTestId('dashboard')).toBeVisible();
  });

  test('Stage 6: Security Status Overview', async ({ page }) => {
    metrics.startJourney('end-user-security-overview');

    // Create account and login
    const persona = EndUserPersona.create();
    await page.goto('http://localhost:3001/signup');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('logged-in');

    // Verify security status card on dashboard
    await expect(page.getByTestId('security-status-card')).toBeVisible();

    // Check security checklist items
    const emailVerified = page.getByTestId('security-email-verified');
    const mfaStatus = page.getByTestId('security-mfa-status');
    const passkeyStatus = page.getByTestId('security-passkey-status');

    await expect(emailVerified).toBeVisible();
    await expect(mfaStatus).toBeVisible();
    await expect(passkeyStatus).toBeVisible();

    // Verify security icons exist
    expect(await emailVerified.locator('.status-icon').count()).toBe(1);
    expect(await mfaStatus.locator('.status-icon').count()).toBe(1);
    expect(await passkeyStatus.locator('.status-icon').count()).toBe(1);

    metrics.checkpoint('security-overview-verified');
  });

  test('Stage 7: Logout Flow', async ({ page }) => {
    metrics.startJourney('end-user-logout');

    // Create account and login
    const persona = EndUserPersona.create();
    await page.goto('http://localhost:3001/signup');
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('logged-in');

    // Verify logged-in state
    await expect(page.getByTestId('dashboard')).toBeVisible();
    await expect(page.getByTestId('logout-button')).toBeVisible();

    // Logout
    await page.getByTestId('logout-button').click();
    await page.waitForURL('**/', { timeout: 5000 });
    metrics.checkpoint('logged-out');

    // Verify logged-out state
    await expect(page.getByTestId('hero-section')).toBeVisible();
    await expect(page.getByTestId('login-button')).toBeVisible();
    await expect(page.getByTestId('signup-button')).toBeVisible();

    // Verify cannot access protected pages
    await page.goto('http://localhost:3001/dashboard');
    await page.waitForURL('**/login', { timeout: 5000 });
    metrics.checkpoint('protected-route-redirect');

    // Should redirect to login
    await expect(page.getByTestId('login-title')).toBeVisible();
  });

  test('Complete End User Journey: Signup → Profile → MFA → Logout', async ({ page }) => {
    metrics.startJourney('end-user-complete');

    const persona = EndUserPersona.create();

    // 1. Signup
    await page.goto('http://localhost:3001');
    await page.getByTestId('signup-button').click();
    await page.getByTestId('name-input').fill(persona.name);
    await page.getByTestId('email-input').fill(persona.email);
    await page.getByTestId('password-input').fill(persona.password);
    await page.getByTestId('signup-submit').click();
    await page.waitForURL('**/dashboard');
    metrics.checkpoint('signup-complete');

    // 2. Update Profile
    await page.getByTestId('profile-link').click();
    await page.waitForURL('**/profile');
    await page.getByTestId('name-input').clear();
    await page.getByTestId('name-input').fill('Updated User Name');
    await page.getByTestId('update-profile-button').click();
    await page.waitForSelector('[data-testid="success-message"]');
    metrics.checkpoint('profile-updated');

    // 3. Setup MFA
    await page.getByTestId('security-link').click();
    await page.waitForURL('**/security');
    await page.getByTestId('enable-mfa-button').click();
    await page.waitForSelector('[data-testid="mfa-setup"]');
    metrics.checkpoint('mfa-setup');

    // 4. Change Password
    await page.getByTestId('current-password-input').fill(persona.password);
    await page.getByTestId('new-password-input').fill('NewPassword123!');
    await page.getByTestId('change-password-button').click();
    await page.waitForSelector('[data-testid="success-message"]');
    metrics.checkpoint('password-changed');

    // 5. Logout
    await page.getByTestId('logout-button').click();
    await page.waitForURL('**/');
    metrics.checkpoint('complete-journey-end');

    // Verify back to landing page
    await expect(page.getByTestId('hero-section')).toBeVisible();
  });
});
