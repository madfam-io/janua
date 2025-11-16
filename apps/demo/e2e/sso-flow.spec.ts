import { test, expect } from '@playwright/test'
import {
  navigateToSSOShowcase,
  navigateToSSOTab,
  createSSOProvider,
  verifySSOProviderInList,
  deleteSSOProvider,
  testSSOConnection,
} from './utils/enterprise-helpers'
import {
  SSO_PROVIDERS,
  SAML_CONFIGS,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
} from './fixtures/enterprise-data'

test.describe('SSO Provider Management', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToSSOShowcase(page)
  })

  test.describe('Provider List View', () => {
    test('should display SSO showcase page with all tabs', async ({ page }) => {
      // Verify page title
      await expect(page.getByRole('heading', { name: 'SSO Configuration' })).toBeVisible()

      // Verify all tabs are present
      await expect(page.getByRole('tab', { name: /providers/i })).toBeVisible()
      await expect(page.getByRole('tab', { name: /configure/i })).toBeVisible()
      await expect(page.getByRole('tab', { name: /saml setup/i })).toBeVisible()
      await expect(page.getByRole('tab', { name: /test/i })).toBeVisible()
    })

    test('should display empty state when no providers exist', async ({ page }) => {
      await navigateToSSOTab(page, 'providers')

      // Verify empty state message
      await expect(
        page.getByText(/no (sso )?providers (configured|found)/i)
      ).toBeVisible()

      // Verify "Add Provider" button is present
      await expect(page.getByRole('button', { name: /add provider/i })).toBeVisible()
    })

    test('should navigate between tabs correctly', async ({ page }) => {
      // Start on Providers tab (default)
      await expect(page.getByRole('tab', { name: /providers/i })).toHaveAttribute(
        'data-state',
        'active'
      )

      // Navigate to Configure tab
      await navigateToSSOTab(page, 'configure')
      await expect(page.getByRole('heading', { name: /create sso provider/i })).toBeVisible()

      // Navigate back to Providers tab
      await navigateToSSOTab(page, 'providers')
      await expect(page.getByRole('tab', { name: /providers/i })).toHaveAttribute(
        'data-state',
        'active'
      )
    })
  })

  test.describe('Create SSO Provider', () => {
    test('should create Google Workspace SAML provider successfully', async ({ page }) => {
      const provider = SSO_PROVIDERS.googleWorkspace

      await createSSOProvider(page, provider)

      // Verify provider appears in list
      await verifySSOProviderInList(page, provider.name, true)

      // Verify provider details
      await navigateToSSOTab(page, 'providers')
      const providerCard = page.locator(`text=${provider.name}`).locator('..')
      await expect(providerCard.getByText(/saml/i)).toBeVisible()
      await expect(providerCard.getByText(/enabled/i)).toBeVisible()
    })

    test('should create Azure AD SAML provider successfully', async ({ page }) => {
      const provider = SSO_PROVIDERS.azureAD

      await createSSOProvider(page, provider)

      // Verify success
      await verifySSOProviderInList(page, provider.name, true)
    })

    test('should create Okta SAML provider successfully', async ({ page }) => {
      const provider = SSO_PROVIDERS.okta

      await createSSOProvider(page, provider)

      // Verify success
      await verifySSOProviderInList(page, provider.name, true)
    })

    test('should create OIDC provider successfully', async ({ page }) => {
      const provider = SSO_PROVIDERS.oidcProvider

      await navigateToSSOTab(page, 'configure')

      // Fill provider details
      await page.getByLabel(/provider name/i).fill(provider.name)
      await page.getByLabel(/provider type/i).click()
      await page.getByRole('option', { name: /oidc/i }).click()

      // Fill OIDC-specific fields
      await page.getByLabel(/client id/i).fill(provider.clientId)
      await page.getByLabel(/issuer/i).fill(provider.issuer)

      // Submit
      await page.getByRole('button', { name: /save|create/i }).click()

      // Verify success
      await expect(page.getByText(/provider (created|saved)/i)).toBeVisible()
      await verifySSOProviderInList(page, provider.name, true)
    })

    test('should create disabled provider successfully', async ({ page }) => {
      const provider = SSO_PROVIDERS.disabledProvider

      await navigateToSSOTab(page, 'configure')

      // Fill provider details
      await page.getByLabel(/provider name/i).fill(provider.name)
      await page.getByLabel(/provider type/i).click()
      await page.getByRole('option', { name: /saml/i }).click()

      // Ensure provider is disabled
      const enabledCheckbox = page.getByLabel(/enable provider/i)
      if (await enabledCheckbox.isChecked()) {
        await enabledCheckbox.click()
      }

      // Submit
      await page.getByRole('button', { name: /save|create/i }).click()

      // Verify success
      await verifySSOProviderInList(page, provider.name, true)

      // Verify disabled status
      const providerCard = page.locator(`text=${provider.name}`).locator('..')
      await expect(providerCard.getByText(/disabled/i)).toBeVisible()
    })

    test('should validate required fields', async ({ page }) => {
      await navigateToSSOTab(page, 'configure')

      // Try to submit without filling required fields
      await page.getByRole('button', { name: /save|create/i }).click()

      // Verify validation errors
      await expect(page.getByText(/provider name is required/i)).toBeVisible()
    })

    test('should validate entity ID format for SAML', async ({ page }) => {
      await navigateToSSOTab(page, 'configure')

      // Fill basic info
      await page.getByLabel(/provider name/i).fill('Invalid SAML Provider')
      await page.getByLabel(/provider type/i).click()
      await page.getByRole('option', { name: /saml/i }).click()

      // Enter invalid entity ID
      await page.getByLabel(/entity id/i).fill('invalid-entity-id')

      // Submit
      await page.getByRole('button', { name: /save|create/i }).click()

      // Verify validation error
      await expect(page.getByText(/invalid entity id/i)).toBeVisible()
    })
  })

  test.describe('Update SSO Provider', () => {
    test('should update provider name successfully', async ({ page }) => {
      // First create a provider
      const originalProvider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, originalProvider)

      // Navigate to edit
      await navigateToSSOTab(page, 'providers')
      const providerCard = page.locator(`text=${originalProvider.name}`).locator('..')
      await providerCard.getByRole('button', { name: /edit/i }).click()

      // Update name
      const newName = 'Updated Google Workspace'
      await page.getByLabel(/provider name/i).clear()
      await page.getByLabel(/provider name/i).fill(newName)

      // Save
      await page.getByRole('button', { name: /save|update/i }).click()

      // Verify update
      await expect(page.getByText(/provider updated/i)).toBeVisible()
      await verifySSOProviderInList(page, newName, true)
      await verifySSOProviderInList(page, originalProvider.name, false)
    })

    test('should toggle provider enabled status', async ({ page }) => {
      // Create an enabled provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Navigate to providers list
      await navigateToSSOTab(page, 'providers')

      // Find toggle switch and click
      const providerCard = page.locator(`text=${provider.name}`).locator('..')
      await providerCard.getByRole('switch', { name: /enable/i }).click()

      // Verify status changed
      await expect(providerCard.getByText(/disabled/i)).toBeVisible()

      // Toggle back
      await providerCard.getByRole('switch', { name: /enable/i }).click()
      await expect(providerCard.getByText(/enabled/i)).toBeVisible()
    })
  })

  test.describe('Delete SSO Provider', () => {
    test('should delete provider successfully', async ({ page }) => {
      // Create a provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Delete it
      await deleteSSOProvider(page, provider.name)

      // Verify deletion
      await verifySSOProviderInList(page, provider.name, false)
    })

    test('should show confirmation dialog before deletion', async ({ page }) => {
      // Create a provider
      const provider = SSO_PROVIDERS.azureAD
      await createSSOProvider(page, provider)

      // Navigate to providers list
      await navigateToSSOTab(page, 'providers')

      // Click delete button
      const providerCard = page.locator(`text=${provider.name}`).locator('..')
      await providerCard.getByRole('button', { name: /delete/i }).click()

      // Verify confirmation dialog appears
      await expect(
        page.getByText(/are you sure|confirm delete/i)
      ).toBeVisible()

      // Verify provider name is mentioned in dialog
      await expect(page.getByText(provider.name)).toBeVisible()

      // Cancel deletion
      await page.getByRole('button', { name: /cancel|no/i }).click()

      // Verify provider still exists
      await verifySSOProviderInList(page, provider.name, true)
    })
  })

  test.describe('SAML Configuration', () => {
    test('should display Service Provider metadata', async ({ page }) => {
      // Create a SAML provider first
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Navigate to SAML config tab
      await navigateToSSOTab(page, 'saml-config')

      // Verify SP metadata is displayed
      await expect(page.getByText(/service provider metadata/i)).toBeVisible()
      await expect(page.getByText(/entity id/i)).toBeVisible()
      await expect(page.getByText(/acs url/i)).toBeVisible()

      // Verify download button exists
      await expect(page.getByRole('button', { name: /download metadata/i })).toBeVisible()
    })

    test('should download Service Provider metadata', async ({ page }) => {
      // Create a SAML provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Navigate to SAML config tab
      await navigateToSSOTab(page, 'saml-config')

      // Set up download promise
      const downloadPromise = page.waitForEvent('download')

      // Click download button
      await page.getByRole('button', { name: /download metadata/i }).click()

      // Wait for download
      const download = await downloadPromise

      // Verify download filename
      expect(download.suggestedFilename()).toMatch(/saml.*metadata.*\.xml/)
    })

    test('should copy Service Provider metadata to clipboard', async ({ page }) => {
      // Create a SAML provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Navigate to SAML config tab
      await navigateToSSOTab(page, 'saml-config')

      // Click copy button
      await page.getByRole('button', { name: /copy metadata/i }).click()

      // Verify success message
      await expect(page.getByText(/copied to clipboard/i)).toBeVisible()
    })

    test('should upload IdP certificate file', async ({ page }) => {
      // Create a SAML provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Navigate to SAML config tab
      await navigateToSSOTab(page, 'saml-config')

      // Prepare mock certificate
      const mockCertificate = '-----BEGIN CERTIFICATE-----\nMOCK\n-----END CERTIFICATE-----'

      // Upload certificate
      const fileChooserPromise = page.waitForEvent('filechooser')
      await page.getByRole('button', { name: /upload certificate/i }).click()
      const fileChooser = await fileChooserPromise
      await fileChooser.setFiles({
        name: 'certificate.pem',
        mimeType: 'application/x-pem-file',
        buffer: Buffer.from(mockCertificate),
      })

      // Verify certificate is loaded
      await expect(page.getByText(/certificate uploaded/i)).toBeVisible()
    })

    test('should configure attribute mapping', async ({ page }) => {
      // Create a SAML provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Navigate to SAML config tab
      await navigateToSSOTab(page, 'saml-config')

      // Configure attribute mapping
      const mapping = SAML_CONFIGS.advanced.attributeMapping!

      await page.getByLabel(/email attribute/i).fill(mapping.email)
      await page.getByLabel(/first name attribute/i).fill(mapping.firstName)
      await page.getByLabel(/last name attribute/i).fill(mapping.lastName)
      await page.getByLabel(/phone attribute/i).fill(mapping.phone)

      // Save configuration
      await page.getByRole('button', { name: /save config/i }).click()

      // Verify success
      await expect(page.getByText(/configuration saved/i)).toBeVisible()
    })

    test('should add custom attribute mappings', async ({ page }) => {
      // Create a SAML provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Navigate to SAML config tab
      await navigateToSSOTab(page, 'saml-config')

      // Add custom mapping
      await page.getByRole('button', { name: /add custom/i }).click()

      // Fill custom attribute
      await page.getByLabel(/custom attribute key/i).fill('department')
      await page.getByLabel(/custom attribute value/i).fill('http://schemas.example.com/department')

      // Save
      await page.getByRole('button', { name: /save config/i }).click()

      // Verify success
      await expect(page.getByText(/configuration saved/i)).toBeVisible()
    })
  })

  test.describe('SSO Connection Testing', () => {
    test('should run metadata validation test', async ({ page }) => {
      // Create a SAML provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Select the provider
      await navigateToSSOTab(page, 'providers')
      const providerCard = page.locator(`text=${provider.name}`).locator('..')
      await providerCard.getByRole('button', { name: /test/i }).click()

      // Run metadata test
      await testSSOConnection(page, 'metadata')

      // Verify results section appears
      await expect(page.getByText(/test results/i)).toBeVisible()
      await expect(page.getByText(/metadata/i)).toBeVisible()
    })

    test('should run full connection test', async ({ page }) => {
      // Create a SAML provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Navigate to test tab
      await navigateToSSOTab(page, 'test')

      // Run full test
      await testSSOConnection(page, 'full')

      // Verify comprehensive results
      await expect(page.getByText(/test results/i)).toBeVisible()
      await expect(page.getByText(/metadata valid/i)).toBeVisible()
      await expect(page.getByText(/certificate valid/i)).toBeVisible()
      await expect(page.getByText(/endpoints reachable/i)).toBeVisible()
    })

    test('should display test results with pass/fail indicators', async ({ page }) => {
      // Create a SAML provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Run test
      await navigateToSSOTab(page, 'test')
      await testSSOConnection(page, 'full')

      // Verify visual indicators
      const resultsSection = page.locator('text=/test results/i').locator('..')

      // Check for success/failure badges
      await expect(
        resultsSection.getByRole('status', { name: /(pass|fail|success|error)/i })
      ).toBeVisible()
    })

    test('should display user attributes from successful auth test', async ({ page }) => {
      // Create a SAML provider
      const provider = SSO_PROVIDERS.googleWorkspace
      await createSSOProvider(page, provider)

      // Run authentication test
      await navigateToSSOTab(page, 'test')
      await page.getByLabel(/authentication test/i).click()
      await page.getByRole('button', { name: /run test/i }).click()

      // Wait for results
      await expect(page.getByText(/test results/i)).toBeVisible({ timeout: 15000 })

      // Verify user attributes section (if auth successful)
      // In mock/test environment, this may show mock attributes
      await expect(page.getByText(/user attributes/i)).toBeVisible()
    })
  })

  test.describe('Quick Start Guides', () => {
    test('should display quick start guides for major IdPs', async ({ page }) => {
      await navigateToSSOTab(page, 'configure')

      // Verify all quick start guides are present
      await expect(page.getByText(/google workspace/i)).toBeVisible()
      await expect(page.getByText(/azure ad/i)).toBeVisible()
      await expect(page.getByText(/okta/i)).toBeVisible()

      // Verify guides have step-by-step instructions
      const googleGuide = page.locator('text=/google workspace/i').locator('..')
      await expect(googleGuide.getByText(/step|1\.|select/i)).toBeVisible()
    })
  })
})
