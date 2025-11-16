import { Page, expect } from '@playwright/test'

/**
 * Enterprise feature test helpers for SSO and Invitations
 */

// ============================================================================
// SSO Test Helpers
// ============================================================================

/**
 * Navigate to SSO showcase page
 */
export async function navigateToSSOShowcase(page: Page) {
  await page.goto('/auth/sso-showcase')
  await expect(page.getByRole('heading', { name: 'SSO Configuration' })).toBeVisible()
}

/**
 * Navigate to specific SSO tab
 */
export async function navigateToSSOTab(page: Page, tab: 'providers' | 'configure' | 'saml-config' | 'test') {
  await page.getByRole('tab', { name: new RegExp(tab, 'i') }).click()
  await page.waitForTimeout(500) // Wait for tab transition
}

/**
 * Create SSO provider through UI
 */
export async function createSSOProvider(
  page: Page,
  provider: {
    name: string
    type: 'saml' | 'oidc' | 'google' | 'azure' | 'okta'
    entityId?: string
    metadataUrl?: string
    enabled?: boolean
  }
) {
  // Navigate to configure tab
  await navigateToSSOTab(page, 'configure')

  // Fill provider name
  await page.getByLabel(/provider name/i).fill(provider.name)

  // Select provider type
  await page.getByLabel(/provider type/i).click()
  await page.getByRole('option', { name: new RegExp(provider.type, 'i') }).click()

  // Fill SAML-specific fields if applicable
  if (provider.type === 'saml' && provider.entityId) {
    await page.getByLabel(/entity id/i).fill(provider.entityId)
  }

  if (provider.type === 'saml' && provider.metadataUrl) {
    await page.getByLabel(/metadata url/i).fill(provider.metadataUrl)
  }

  // Toggle enabled state if specified
  if (provider.enabled !== undefined) {
    const checkbox = page.getByLabel(/enable provider/i)
    const isChecked = await checkbox.isChecked()
    if (isChecked !== provider.enabled) {
      await checkbox.click()
    }
  }

  // Submit form
  await page.getByRole('button', { name: /save|create provider/i }).click()

  // Wait for success indication
  await expect(page.getByText(/provider (created|saved)/i)).toBeVisible({ timeout: 5000 })
}

/**
 * Verify SSO provider appears in list
 */
export async function verifySSOProviderInList(
  page: Page,
  providerName: string,
  shouldExist: boolean = true
) {
  await navigateToSSOTab(page, 'providers')
  const providerCard = page.getByText(providerName)

  if (shouldExist) {
    await expect(providerCard).toBeVisible()
  } else {
    await expect(providerCard).not.toBeVisible()
  }
}

/**
 * Delete SSO provider
 */
export async function deleteSSOProvider(page: Page, providerName: string) {
  await navigateToSSOTab(page, 'providers')

  // Find provider card and click delete
  const providerCard = page.locator(`text=${providerName}`).locator('..')
  await providerCard.getByRole('button', { name: /delete/i }).click()

  // Confirm deletion
  await page.getByRole('button', { name: /confirm|yes|delete/i }).click()

  // Wait for deletion success
  await expect(page.getByText(/provider deleted/i)).toBeVisible({ timeout: 5000 })
}

/**
 * Test SSO connection
 */
export async function testSSOConnection(
  page: Page,
  testType: 'metadata' | 'authentication' | 'full' = 'full'
) {
  await navigateToSSOTab(page, 'test')

  // Select test type
  await page.getByLabel(new RegExp(testType, 'i')).click()

  // Run test
  await page.getByRole('button', { name: /run test|test connection/i }).click()

  // Wait for test results
  await expect(page.getByText(/test (complete|result)/i)).toBeVisible({ timeout: 10000 })
}

// ============================================================================
// Invitation Test Helpers
// ============================================================================

/**
 * Navigate to Invitations showcase page
 */
export async function navigateToInvitationsShowcase(page: Page) {
  await page.goto('/auth/invitations-showcase')
  await expect(page.getByRole('heading', { name: 'Organization Invitations' })).toBeVisible()
}

/**
 * Navigate to specific Invitations tab
 */
export async function navigateToInvitationsTab(
  page: Page,
  tab: 'manage' | 'invite' | 'bulk' | 'accept'
) {
  await page.getByRole('tab', { name: new RegExp(tab, 'i') }).click()
  await page.waitForTimeout(500) // Wait for tab transition
}

/**
 * Create single invitation through UI
 */
export async function createInvitation(
  page: Page,
  invitation: {
    email: string
    role?: 'member' | 'admin' | 'owner'
    message?: string
    expiresIn?: number
  }
) {
  // Navigate to invite tab
  await navigateToInvitationsTab(page, 'invite')

  // Fill email
  await page.getByLabel(/email/i).fill(invitation.email)

  // Select role if specified
  if (invitation.role) {
    await page.getByLabel(/role/i).click()
    await page.getByRole('option', { name: new RegExp(invitation.role, 'i') }).click()
  }

  // Fill message if specified
  if (invitation.message) {
    await page.getByLabel(/message/i).fill(invitation.message)
  }

  // Set expiration if specified
  if (invitation.expiresIn) {
    await page.getByLabel(/expires in/i).fill(String(invitation.expiresIn))
  }

  // Submit form
  await page.getByRole('button', { name: /send invitation/i }).click()

  // Wait for success indication
  await expect(page.getByText(/invitation sent/i)).toBeVisible({ timeout: 5000 })
}

/**
 * Upload CSV for bulk invitations
 */
export async function uploadBulkInvitations(page: Page, csvContent: string) {
  // Navigate to bulk tab
  await navigateToInvitationsTab(page, 'bulk')

  // Option 1: File upload
  const fileChooserPromise = page.waitForEvent('filechooser')
  await page.getByLabel(/upload (csv|file)/i).click()
  const fileChooser = await fileChooserPromise

  // Create temporary file with CSV content
  const buffer = Buffer.from(csvContent, 'utf-8')
  await fileChooser.setFiles({
    name: 'invitations.csv',
    mimeType: 'text/csv',
    buffer,
  })

  // Wait for CSV parsing
  await expect(page.getByText(/preview/i)).toBeVisible({ timeout: 3000 })
}

/**
 * Paste CSV content for bulk invitations
 */
export async function pasteBulkInvitations(page: Page, csvContent: string) {
  // Navigate to bulk tab
  await navigateToInvitationsTab(page, 'bulk')

  // Click paste option
  await page.getByRole('button', { name: /paste csv/i }).click()

  // Fill textarea with CSV content
  await page.getByLabel(/csv content/i).fill(csvContent)

  // Submit
  await page.getByRole('button', { name: /parse|preview/i }).click()

  // Wait for preview
  await expect(page.getByText(/preview/i)).toBeVisible({ timeout: 3000 })
}

/**
 * Submit bulk invitations after preview
 */
export async function submitBulkInvitations(page: Page) {
  await page.getByRole('button', { name: /send (all )?invitations/i }).click()

  // Wait for results
  await expect(page.getByText(/invitation(s)? sent/i)).toBeVisible({ timeout: 10000 })
}

/**
 * Verify invitation appears in list
 */
export async function verifyInvitationInList(
  page: Page,
  email: string,
  shouldExist: boolean = true
) {
  await navigateToInvitationsTab(page, 'manage')

  // Search for email
  await page.getByPlaceholder(/search/i).fill(email)
  await page.waitForTimeout(500) // Wait for filter

  const invitationRow = page.getByText(email)

  if (shouldExist) {
    await expect(invitationRow).toBeVisible()
  } else {
    await expect(invitationRow).not.toBeVisible()
  }
}

/**
 * Resend invitation
 */
export async function resendInvitation(page: Page, email: string) {
  await navigateToInvitationsTab(page, 'manage')

  // Find invitation and click resend
  const invitationRow = page.locator(`text=${email}`).locator('..')
  await invitationRow.getByRole('button', { name: /resend/i }).click()

  // Wait for confirmation
  await expect(page.getByText(/invitation resent/i)).toBeVisible({ timeout: 5000 })
}

/**
 * Revoke invitation
 */
export async function revokeInvitation(page: Page, email: string) {
  await navigateToInvitationsTab(page, 'manage')

  // Find invitation and click revoke
  const invitationRow = page.locator(`text=${email}`).locator('..')
  await invitationRow.getByRole('button', { name: /revoke/i }).click()

  // Confirm revocation
  await page.getByRole('button', { name: /confirm|yes|revoke/i }).click()

  // Wait for confirmation
  await expect(page.getByText(/invitation revoked/i)).toBeVisible({ timeout: 5000 })
}

/**
 * Filter invitations by status
 */
export async function filterInvitationsByStatus(
  page: Page,
  status: 'pending' | 'accepted' | 'expired' | 'revoked' | ''
) {
  await navigateToInvitationsTab(page, 'manage')

  await page.getByLabel(/filter by status/i).click()
  if (status) {
    await page.getByRole('option', { name: new RegExp(status, 'i') }).click()
  } else {
    await page.getByRole('option', { name: /all/i }).click()
  }

  await page.waitForTimeout(500) // Wait for filter
}

/**
 * Get invitation statistics
 */
export async function getInvitationStats(page: Page): Promise<{
  total: number
  pending: number
  accepted: number
  expired: number
}> {
  await navigateToInvitationsTab(page, 'manage')

  const totalText = await page.getByText(/total:/i).textContent()
  const pendingText = await page.getByText(/pending:/i).textContent()
  const acceptedText = await page.getByText(/accepted:/i).textContent()
  const expiredText = await page.getByText(/expired:/i).textContent()

  return {
    total: parseInt(totalText?.match(/\d+/)?.[0] || '0'),
    pending: parseInt(pendingText?.match(/\d+/)?.[0] || '0'),
    accepted: parseInt(acceptedText?.match(/\d+/)?.[0] || '0'),
    expired: parseInt(expiredText?.match(/\d+/)?.[0] || '0'),
  }
}

/**
 * Copy invitation URL
 */
export async function copyInvitationUrl(page: Page, email: string): Promise<string> {
  await navigateToInvitationsTab(page, 'manage')

  // Find invitation and click copy URL
  const invitationRow = page.locator(`text=${email}`).locator('..')
  await invitationRow.getByRole('button', { name: /copy (url|link)/i }).click()

  // Get URL from clipboard (in real tests, this would use clipboard API)
  // For now, return a mock URL
  return 'http://localhost:3000/accept-invitation?token=mock-token'
}

/**
 * Accept invitation (demo flow)
 */
export async function acceptInvitation(
  page: Page,
  options: {
    isNewUser: boolean
    name?: string
    password?: string
  }
) {
  // Should already be on accept tab
  await navigateToInvitationsTab(page, 'accept')

  // Generate demo token
  await page.getByRole('button', { name: /generate demo/i }).click()

  // Wait for invitation details to load
  await expect(page.getByText(/you're invited/i)).toBeVisible({ timeout: 5000 })

  if (options.isNewUser) {
    // Select "Create Account" option
    await page.getByRole('button', { name: /create account/i }).click()

    // Fill name and password
    if (options.name) {
      await page.getByLabel(/full name/i).fill(options.name)
    }

    if (options.password) {
      await page.getByLabel(/^password$/i).fill(options.password)
      await page.getByLabel(/confirm password/i).fill(options.password)
    }

    // Submit
    await page.getByRole('button', { name: /accept.*create/i }).click()
  } else {
    // Select "Sign In" option
    await page.getByRole('button', { name: /sign in/i }).click()

    // Would redirect to sign-in page in real flow
  }

  // Wait for acceptance confirmation
  await expect(page.getByText(/invitation accepted/i)).toBeVisible({ timeout: 5000 })
}

// ============================================================================
// CSV Generation Helpers
// ============================================================================

/**
 * Generate CSV content for bulk invitations
 */
export function generateBulkInvitationsCSV(
  invitations: Array<{
    email: string
    role?: string
    message?: string
  }>
): string {
  const header = 'email,role,message'
  const rows = invitations.map(
    (inv) =>
      `${inv.email},${inv.role || ''},${inv.message?.replace(/,/g, ';') || ''}`
  )
  return [header, ...rows].join('\n')
}

/**
 * Generate invalid CSV for testing error handling
 */
export function generateInvalidCSV(): string {
  return 'invalid,csv,format\nno@email,role,message\n@invalid.com,admin,test'
}

// ============================================================================
// Wait Helpers
// ============================================================================

/**
 * Wait for SSO provider list to load
 */
export async function waitForSSOProvidersLoad(page: Page) {
  await expect(
    page.getByText(/loading|no providers/i)
  ).toBeVisible({ timeout: 10000 })
}

/**
 * Wait for invitation list to load
 */
export async function waitForInvitationsLoad(page: Page) {
  await expect(
    page.getByText(/loading|no invitations/i)
  ).toBeVisible({ timeout: 10000 })
}
