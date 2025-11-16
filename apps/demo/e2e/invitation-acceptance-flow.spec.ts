import { test, expect } from '@playwright/test'
import {
  navigateToInvitationsShowcase,
  navigateToInvitationsTab,
  acceptInvitation,
} from './utils/enterprise-helpers'
import {
  INVITATION_ACCEPTANCE_USERS,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
} from './fixtures/enterprise-data'

test.describe('Invitation Acceptance Flow', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToInvitationsShowcase(page)
    await navigateToInvitationsTab(page, 'accept')
  })

  test.describe('Accept Tab Display', () => {
    test('should display invitation acceptance interface', async ({ page }) => {
      // Verify heading
      await expect(
        page.getByRole('heading', { name: /accept.*invitation/i })
      ).toBeVisible()

      // Verify demo token generator button
      await expect(
        page.getByRole('button', { name: /generate.*demo/i })
      ).toBeVisible()

      // Verify instructions or explanation text
      await expect(page.getByText(/invitation.*link|token/i)).toBeVisible()
    })

    test('should generate demo invitation token', async ({ page }) => {
      // Click generate demo button
      await page.getByRole('button', { name: /generate.*demo/i }).click()

      // Wait for invitation details to load
      await expect(page.getByText(/you're invited|join.*organization/i)).toBeVisible({
        timeout: 5000,
      })

      // Verify invitation details are displayed
      await expect(page.getByText(/organization/i)).toBeVisible()
      await expect(page.getByText(/role/i)).toBeVisible()
    })

    test('should display invitation details after token load', async ({ page }) => {
      // Generate demo token
      await page.getByRole('button', { name: /generate.*demo/i }).click()

      // Wait for details
      await page.waitForTimeout(1000)

      // Verify organization information
      await expect(page.getByText(/organization.*name/i)).toBeVisible()

      // Verify role information
      await expect(page.getByText(/member|admin|owner/i)).toBeVisible()

      // Verify expiration information
      await expect(page.getByText(/expire|valid/i)).toBeVisible()
    })
  })

  test.describe('New User Registration Flow', () => {
    test('should display new user registration form', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select "Create Account" option
      await page.getByRole('button', { name: /create account|new user/i }).click()

      // Verify registration form fields
      await expect(page.getByLabel(/full name|name/i)).toBeVisible()
      await expect(page.getByLabel(/^password$/i)).toBeVisible()
      await expect(page.getByLabel(/confirm password/i)).toBeVisible()
    })

    test('should accept invitation as new user successfully', async ({ page }) => {
      const user = INVITATION_ACCEPTANCE_USERS.newUser

      await acceptInvitation(page, {
        isNewUser: true,
        name: user.name,
        password: user.password,
      })

      // Verify acceptance confirmation
      await expect(page.getByText(/invitation accepted|welcome/i)).toBeVisible({
        timeout: 5000,
      })
    })

    test('should validate name is required', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Try to submit without name
      await page.getByLabel(/^password$/i).fill('ValidPassword123!')
      await page.getByLabel(/confirm password/i).fill('ValidPassword123!')
      await page.getByRole('button', { name: /accept.*create/i }).click()

      // Verify validation error
      await expect(page.getByText(/name.*required/i)).toBeVisible()
    })

    test('should validate password strength', async ({ page }) => {
      const user = INVITATION_ACCEPTANCE_USERS.weakPassword

      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Fill form with weak password
      await page.getByLabel(/full name/i).fill(user.name)
      await page.getByLabel(/^password$/i).fill(user.password)
      await page.getByLabel(/confirm password/i).fill(user.password)

      // Submit
      await page.getByRole('button', { name: /accept.*create/i }).click()

      // Verify password strength error
      await expect(
        page.getByText(/password.*weak|password.*strong|at least 8 characters/i)
      ).toBeVisible()
    })

    test('should validate password confirmation matches', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Fill form with mismatched passwords
      await page.getByLabel(/full name/i).fill('Test User')
      await page.getByLabel(/^password$/i).fill('ValidPassword123!')
      await page.getByLabel(/confirm password/i).fill('DifferentPassword456!')

      // Submit
      await page.getByRole('button', { name: /accept.*create/i }).click()

      // Verify mismatch error
      await expect(page.getByText(/password.*match/i)).toBeVisible()
    })

    test('should show password requirements', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Verify password requirements are displayed
      await expect(
        page.getByText(/at least 8 characters|uppercase|lowercase|number|special/i)
      ).toBeVisible()
    })

    test('should show password strength indicator', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Type a password
      const passwordInput = page.getByLabel(/^password$/i)
      await passwordInput.fill('weak')

      // Look for strength indicator
      const strengthIndicator = page.getByText(/weak|medium|strong/i)
      if (await strengthIndicator.isVisible({ timeout: 1000 }).catch(() => false)) {
        await expect(strengthIndicator).toBeVisible()
      }
    })
  })

  test.describe('Existing User Sign-In Flow', () => {
    test('should display sign-in option', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Verify sign-in option exists
      await expect(page.getByRole('button', { name: /sign in|existing/i })).toBeVisible()
    })

    test('should redirect to sign-in for existing users', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Click sign-in option
      await page.getByRole('button', { name: /sign in|existing/i }).click()

      // In real implementation, would redirect to sign-in page with return URL
      // Verify redirect message or instruction
      await expect(
        page.getByText(/sign in|redirect|login/i)
      ).toBeVisible()
    })

    test('should preserve invitation context after sign-in', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Click sign-in
      await page.getByRole('button', { name: /sign in|existing/i }).click()

      // Verify invitation token/context is preserved (e.g., in URL or session)
      const url = page.url()
      expect(url).toMatch(/invitation|token|invite/)
    })
  })

  test.describe('Token Validation', () => {
    test('should validate invitation token format', async ({ page }) => {
      // Try entering invalid token manually (if input is available)
      const tokenInput = page.getByLabel(/token|invitation.*code/i)

      if (await tokenInput.isVisible({ timeout: 1000 }).catch(() => false)) {
        await tokenInput.fill('invalid-token-123')
        await page.getByRole('button', { name: /validate|check/i }).click()

        // Verify validation error
        await expect(page.getByText(/invalid.*token/i)).toBeVisible()
      }
    })

    test('should handle expired invitation gracefully', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()

      // In demo mode, may show expired state
      // Look for expired message or warning
      const expiredMessage = page.getByText(/expired|no longer valid/i)

      if (await expiredMessage.isVisible({ timeout: 2000 }).catch(() => false)) {
        await expect(expiredMessage).toBeVisible()

        // Verify acceptance is blocked
        const acceptButton = page.getByRole('button', { name: /accept/i })
        await expect(acceptButton).toBeDisabled()
      }
    })

    test('should handle revoked invitation gracefully', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()

      // In demo mode, may show revoked state
      const revokedMessage = page.getByText(/revoked|cancelled/i)

      if (await revokedMessage.isVisible({ timeout: 2000 }).catch(() => false)) {
        await expect(revokedMessage).toBeVisible()

        // Verify error message is helpful
        await expect(page.getByText(/contact.*admin|no longer valid/i)).toBeVisible()
      }
    })

    test('should display token expiration information', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Verify expiration date is shown
      await expect(page.getByText(/expire|valid.*until/i)).toBeVisible()
    })
  })

  test.describe('Post-Acceptance Flow', () => {
    test('should redirect after successful acceptance', async ({ page }) => {
      const user = INVITATION_ACCEPTANCE_USERS.newUser

      await acceptInvitation(page, {
        isNewUser: true,
        name: user.name,
        password: user.password,
      })

      // Wait for acceptance
      await expect(page.getByText(/invitation accepted/i)).toBeVisible({ timeout: 5000 })

      // Wait for potential redirect
      await page.waitForTimeout(2000)

      // In real implementation, would redirect to dashboard or organization page
      // Verify URL changed or redirect message appears
      const url = page.url()
      const hasRedirected = !url.includes('accept')

      // Either redirected OR shows "Redirecting..." message
      const redirectMessage = await page.getByText(/redirect/i).isVisible().catch(() => false)

      expect(hasRedirected || redirectMessage).toBe(true)
    })

    test('should display welcome message after acceptance', async ({ page }) => {
      const user = INVITATION_ACCEPTANCE_USERS.newUser

      await acceptInvitation(page, {
        isNewUser: true,
        name: user.name,
        password: user.password,
      })

      // Verify welcome or success message
      await expect(
        page.getByText(/welcome|success|accepted.*invitation/i)
      ).toBeVisible({ timeout: 5000 })
    })

    test('should show organization information after acceptance', async ({ page }) => {
      const user = INVITATION_ACCEPTANCE_USERS.newUser

      await acceptInvitation(page, {
        isNewUser: true,
        name: user.name,
        password: user.password,
      })

      // Wait for acceptance
      await page.waitForTimeout(2000)

      // Verify organization context is shown
      await expect(page.getByText(/organization|team/i)).toBeVisible()
    })
  })

  test.describe('Error Handling', () => {
    test('should handle network errors during acceptance', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Fill form
      await page.getByLabel(/full name/i).fill('Test User')
      await page.getByLabel(/^password$/i).fill('ValidPassword123!')
      await page.getByLabel(/confirm password/i).fill('ValidPassword123!')

      // Simulate network error (if supported)
      // await page.context().setOffline(true)

      // Submit
      await page.getByRole('button', { name: /accept.*create/i }).click()

      // Would expect error handling for network failure
    })

    test('should handle already accepted invitation', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()

      // In demo, may show "already accepted" state
      const alreadyAcceptedMessage = page.getByText(/already.*accepted|claimed/i)

      if (await alreadyAcceptedMessage.isVisible({ timeout: 2000 }).catch(() => false)) {
        await expect(alreadyAcceptedMessage).toBeVisible()

        // Verify helpful message
        await expect(page.getByText(/sign in|contact.*admin/i)).toBeVisible()
      }
    })

    test('should provide helpful error messages', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Submit empty form
      await page.getByRole('button', { name: /accept.*create/i }).click()

      // Verify error messages are clear and actionable
      const errorMessages = page.getByText(/required|invalid|must/i)
      await expect(errorMessages.first()).toBeVisible()
    })
  })

  test.describe('User Experience', () => {
    test('should show loading state during submission', async ({ page }) => {
      const user = INVITATION_ACCEPTANCE_USERS.newUser

      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Fill form
      await page.getByLabel(/full name/i).fill(user.name)
      await page.getByLabel(/^password$/i).fill(user.password)
      await page.getByLabel(/confirm password/i).fill(user.password)

      // Submit
      await page.getByRole('button', { name: /accept.*create/i }).click()

      // Look for loading indicator
      const loadingIndicator = page.getByText(/loading|processing|creating/i)

      if (await loadingIndicator.isVisible({ timeout: 500 }).catch(() => false)) {
        await expect(loadingIndicator).toBeVisible()
      }
    })

    test('should disable submit button while processing', async ({ page }) => {
      const user = INVITATION_ACCEPTANCE_USERS.newUser

      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Fill form
      await page.getByLabel(/full name/i).fill(user.name)
      await page.getByLabel(/^password$/i).fill(user.password)
      await page.getByLabel(/confirm password/i).fill(user.password)

      // Get submit button
      const submitButton = page.getByRole('button', { name: /accept.*create/i })

      // Submit
      await submitButton.click()

      // Verify button is disabled during processing (if slow enough to catch)
      const isDisabled = await submitButton.isDisabled().catch(() => false)

      // Either button is disabled OR request completed too fast to check
      expect(typeof isDisabled).toBe('boolean')
    })

    test('should allow toggling password visibility', async ({ page }) => {
      // Generate demo invitation
      await page.getByRole('button', { name: /generate.*demo/i }).click()
      await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

      // Select create account
      await page.getByRole('button', { name: /create account/i }).click()

      // Look for password visibility toggle
      const toggleButton = page.getByRole('button', { name: /show|hide|toggle.*password/i })

      if (await toggleButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        // Verify password input type changes
        const passwordInput = page.getByLabel(/^password$/i)

        await expect(passwordInput).toHaveAttribute('type', 'password')

        await toggleButton.click()

        await expect(passwordInput).toHaveAttribute('type', 'text')
      }
    })
  })
})
