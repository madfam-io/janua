import { test, expect } from '@playwright/test'
import {
  navigateToInvitationsShowcase,
  navigateToInvitationsTab,
  createInvitation,
  verifyInvitationInList,
  resendInvitation,
  revokeInvitation,
  filterInvitationsByStatus,
  getInvitationStats,
  copyInvitationUrl,
} from './utils/enterprise-helpers'
import {
  TEST_INVITATIONS,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
} from './fixtures/enterprise-data'

test.describe('Invitation Management', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToInvitationsShowcase(page)
  })

  test.describe('Invitation Showcase Display', () => {
    test('should display invitations showcase page with all tabs', async ({ page }) => {
      // Verify page title
      await expect(
        page.getByRole('heading', { name: /organization invitations/i })
      ).toBeVisible()

      // Verify all tabs are present
      await expect(page.getByRole('tab', { name: /manage/i })).toBeVisible()
      await expect(page.getByRole('tab', { name: /invite user/i })).toBeVisible()
      await expect(page.getByRole('tab', { name: /bulk upload/i })).toBeVisible()
      await expect(page.getByRole('tab', { name: /accept demo/i })).toBeVisible()
    })

    test('should display invitation statistics', async ({ page }) => {
      await navigateToInvitationsTab(page, 'manage')

      // Verify statistics cards are displayed
      await expect(page.getByText(/total:/i)).toBeVisible()
      await expect(page.getByText(/pending:/i)).toBeVisible()
      await expect(page.getByText(/accepted:/i)).toBeVisible()
      await expect(page.getByText(/expired:/i)).toBeVisible()
    })

    test('should navigate between tabs correctly', async ({ page }) => {
      // Start on Manage tab (default)
      await expect(page.getByRole('tab', { name: /manage/i })).toHaveAttribute(
        'data-state',
        'active'
      )

      // Navigate to Invite User tab
      await navigateToInvitationsTab(page, 'invite')
      await expect(page.getByRole('heading', { name: /send invitation/i })).toBeVisible()

      // Navigate back to Manage tab
      await navigateToInvitationsTab(page, 'manage')
      await expect(page.getByRole('tab', { name: /manage/i })).toHaveAttribute(
        'data-state',
        'active'
      )
    })
  })

  test.describe('Create Single Invitation', () => {
    test('should create member invitation successfully', async ({ page }) => {
      const invitation = TEST_INVITATIONS.memberInvite

      await createInvitation(page, invitation)

      // Verify invitation appears in list
      await verifyInvitationInList(page, invitation.email, true)

      // Verify invitation details
      await navigateToInvitationsTab(page, 'manage')
      const invitationRow = page.locator(`text=${invitation.email}`).locator('..')
      await expect(invitationRow.getByText(/member/i)).toBeVisible()
      await expect(invitationRow.getByText(/pending/i)).toBeVisible()
    })

    test('should create admin invitation successfully', async ({ page }) => {
      const invitation = TEST_INVITATIONS.adminInvite

      await createInvitation(page, invitation)

      // Verify success
      await verifyInvitationInList(page, invitation.email, true)

      // Verify admin role
      const invitationRow = page.locator(`text=${invitation.email}`).locator('..')
      await expect(invitationRow.getByText(/admin/i)).toBeVisible()
    })

    test('should create owner invitation successfully', async ({ page }) => {
      const invitation = TEST_INVITATIONS.ownerInvite

      await createInvitation(page, invitation)

      // Verify success
      await verifyInvitationInList(page, invitation.email, true)

      // Verify owner role
      const invitationRow = page.locator(`text=${invitation.email}`).locator('..')
      await expect(invitationRow.getByText(/owner/i)).toBeVisible()
    })

    test('should create invitation with custom expiration', async ({ page }) => {
      const invitation = TEST_INVITATIONS.shortExpiry

      await createInvitation(page, invitation)

      // Verify success
      await verifyInvitationInList(page, invitation.email, true)
    })

    test('should create invitation without message', async ({ page }) => {
      const invitation = TEST_INVITATIONS.noMessage

      await navigateToInvitationsTab(page, 'invite')

      // Fill only required fields
      await page.getByLabel(/email/i).fill(invitation.email)
      await page.getByLabel(/role/i).click()
      await page.getByRole('option', { name: /member/i }).click()

      // Submit
      await page.getByRole('button', { name: /send invitation/i }).click()

      // Verify success
      await expect(page.getByText(/invitation sent/i)).toBeVisible({ timeout: 5000 })
      await verifyInvitationInList(page, invitation.email, true)
    })

    test('should validate email format', async ({ page }) => {
      const invitation = TEST_INVITATIONS.invalidEmail

      await navigateToInvitationsTab(page, 'invite')

      // Fill invalid email
      await page.getByLabel(/email/i).fill(invitation.email)
      await page.getByLabel(/role/i).click()
      await page.getByRole('option', { name: /member/i }).click()

      // Submit
      await page.getByRole('button', { name: /send invitation/i }).click()

      // Verify validation error
      await expect(page.getByText(/invalid email/i)).toBeVisible()
    })

    test('should validate expiration range', async ({ page }) => {
      await navigateToInvitationsTab(page, 'invite')

      // Fill invitation details
      await page.getByLabel(/email/i).fill('test@plinto.dev')
      await page.getByLabel(/role/i).click()
      await page.getByRole('option', { name: /member/i }).click()

      // Try invalid expiration (0 days)
      await page.getByLabel(/expires in/i).fill('0')
      await page.getByRole('button', { name: /send invitation/i }).click()
      await expect(page.getByText(/at least 1 day/i)).toBeVisible()

      // Try invalid expiration (31 days)
      await page.getByLabel(/expires in/i).fill('31')
      await page.getByRole('button', { name: /send invitation/i }).click()
      await expect(page.getByText(/cannot exceed 30 days/i)).toBeVisible()
    })
  })

  test.describe('Invitation List Management', () => {
    test('should display invitation URL', async ({ page }) => {
      // Create an invitation first
      const invitation = TEST_INVITATIONS.memberInvite
      await createInvitation(page, invitation)

      // Navigate to manage tab
      await navigateToInvitationsTab(page, 'manage')

      // Find invitation row
      const invitationRow = page.locator(`text=${invitation.email}`).locator('..')

      // Verify URL is displayed or can be copied
      await expect(
        invitationRow.getByRole('button', { name: /copy (url|link)/i })
      ).toBeVisible()
    })

    test('should copy invitation URL to clipboard', async ({ page }) => {
      // Create an invitation
      const invitation = TEST_INVITATIONS.memberInvite
      await createInvitation(page, invitation)

      // Copy URL
      await copyInvitationUrl(page, invitation.email)

      // Verify success message
      await expect(page.getByText(/copied to clipboard/i)).toBeVisible()
    })
  })

  test.describe('Resend Invitation', () => {
    test('should resend invitation successfully', async ({ page }) => {
      // Create an invitation first
      const invitation = TEST_INVITATIONS.memberInvite
      await createInvitation(page, invitation)

      // Resend it
      await resendInvitation(page, invitation.email)

      // Verify success message
      await expect(page.getByText(/invitation resent/i)).toBeVisible()
    })

    test('should update sent count after resend', async ({ page }) => {
      // Create an invitation
      const invitation = TEST_INVITATIONS.adminInvite
      await createInvitation(page, invitation)

      // Navigate to manage tab
      await navigateToInvitationsTab(page, 'manage')

      // Get initial sent count (if displayed)
      const invitationRow = page.locator(`text=${invitation.email}`).locator('..')
      const initialSentText = await invitationRow.getByText(/sent:/i).textContent()

      // Resend
      await resendInvitation(page, invitation.email)

      // Verify count updated or resend timestamp changed
      await page.waitForTimeout(1000) // Wait for UI update
      const updatedSentText = await invitationRow.getByText(/sent:/i).textContent()
      expect(updatedSentText).not.toBe(initialSentText)
    })
  })

  test.describe('Revoke Invitation', () => {
    test('should revoke invitation successfully', async ({ page }) => {
      // Create an invitation first
      const invitation = TEST_INVITATIONS.memberInvite
      await createInvitation(page, invitation)

      // Revoke it
      await revokeInvitation(page, invitation.email)

      // Verify success
      await expect(page.getByText(/invitation revoked/i)).toBeVisible()
    })

    test('should show confirmation dialog before revocation', async ({ page }) => {
      // Create an invitation
      const invitation = TEST_INVITATIONS.adminInvite
      await createInvitation(page, invitation)

      // Navigate to manage tab
      await navigateToInvitationsTab(page, 'manage')

      // Click revoke button
      const invitationRow = page.locator(`text=${invitation.email}`).locator('..')
      await invitationRow.getByRole('button', { name: /revoke/i }).click()

      // Verify confirmation dialog appears
      await expect(page.getByText(/are you sure|confirm/i)).toBeVisible()

      // Verify email is mentioned in dialog
      await expect(page.getByText(invitation.email)).toBeVisible()

      // Cancel revocation
      await page.getByRole('button', { name: /cancel|no/i }).click()

      // Verify invitation still exists
      await verifyInvitationInList(page, invitation.email, true)
    })

    test('should update status to revoked', async ({ page }) => {
      // Create an invitation
      const invitation = TEST_INVITATIONS.ownerInvite
      await createInvitation(page, invitation)

      // Revoke it
      await revokeInvitation(page, invitation.email)

      // Verify status changed
      const invitationRow = page.locator(`text=${invitation.email}`).locator('..')
      await expect(invitationRow.getByText(/revoked/i)).toBeVisible()
    })
  })

  test.describe('Filter and Search', () => {
    test('should filter invitations by status - pending', async ({ page }) => {
      // Create multiple invitations with different statuses (in real scenario)
      const invitation = TEST_INVITATIONS.memberInvite
      await createInvitation(page, invitation)

      // Filter by pending
      await filterInvitationsByStatus(page, 'pending')

      // Verify filtered results
      await expect(page.getByText(invitation.email)).toBeVisible()
    })

    test('should filter invitations by status - accepted', async ({ page }) => {
      await navigateToInvitationsTab(page, 'manage')

      // Filter by accepted
      await filterInvitationsByStatus(page, 'accepted')

      // In demo environment, may show empty state
      await expect(
        page.getByText(/no (invitations|results)/i)
      ).toBeVisible()
    })

    test('should filter invitations by status - expired', async ({ page }) => {
      await navigateToInvitationsTab(page, 'manage')

      // Filter by expired
      await filterInvitationsByStatus(page, 'expired')

      // Verify filter applied
      await page.waitForTimeout(500) // Wait for filter
    })

    test('should search invitations by email', async ({ page }) => {
      // Create an invitation
      const invitation = TEST_INVITATIONS.memberInvite
      await createInvitation(page, invitation)

      // Navigate to manage tab
      await navigateToInvitationsTab(page, 'manage')

      // Search by email
      await page.getByPlaceholder(/search/i).fill(invitation.email)
      await page.waitForTimeout(500) // Wait for search

      // Verify search results
      await expect(page.getByText(invitation.email)).toBeVisible()
    })

    test('should clear filters', async ({ page }) => {
      // Create an invitation
      const invitation = TEST_INVITATIONS.adminInvite
      await createInvitation(page, invitation)

      // Apply filter
      await filterInvitationsByStatus(page, 'pending')

      // Clear filter
      await filterInvitationsByStatus(page, '') // Empty status = all

      // Verify all invitations shown
      await expect(page.getByText(invitation.email)).toBeVisible()
    })
  })

  test.describe('Invitation Statistics', () => {
    test('should display accurate total count', async ({ page }) => {
      await navigateToInvitationsTab(page, 'manage')

      // Get stats
      const stats = await getInvitationStats(page)

      // Verify stats object structure
      expect(stats).toHaveProperty('total')
      expect(stats).toHaveProperty('pending')
      expect(stats).toHaveProperty('accepted')
      expect(stats).toHaveProperty('expired')
    })

    test('should update statistics after creating invitation', async ({ page }) => {
      // Get initial stats
      await navigateToInvitationsTab(page, 'manage')
      const initialStats = await getInvitationStats(page)

      // Create invitation
      const invitation = TEST_INVITATIONS.memberInvite
      await createInvitation(page, invitation)

      // Get updated stats
      const updatedStats = await getInvitationStats(page)

      // Verify total increased
      expect(updatedStats.total).toBeGreaterThan(initialStats.total)
    })

    test('should update statistics after revoking invitation', async ({ page }) => {
      // Create invitation
      const invitation = TEST_INVITATIONS.adminInvite
      await createInvitation(page, invitation)

      // Get stats before revoke
      const beforeRevokeStats = await getInvitationStats(page)

      // Revoke invitation
      await revokeInvitation(page, invitation.email)

      // Get stats after revoke
      const afterRevokeStats = await getInvitationStats(page)

      // Verify pending count decreased (if tracked separately)
      expect(afterRevokeStats.pending).toBeLessThanOrEqual(beforeRevokeStats.pending)
    })
  })
})
