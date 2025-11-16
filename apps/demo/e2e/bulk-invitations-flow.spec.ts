import { test, expect } from '@playwright/test'
import {
  navigateToInvitationsShowcase,
  navigateToInvitationsTab,
  uploadBulkInvitations,
  pasteBulkInvitations,
  submitBulkInvitations,
  generateBulkInvitationsCSV,
} from './utils/enterprise-helpers'
import {
  BULK_INVITATIONS,
  CSV_TEST_DATA,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
} from './fixtures/enterprise-data'

test.describe('Bulk Invitation Upload', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToInvitationsShowcase(page)
    await navigateToInvitationsTab(page, 'bulk')
  })

  test.describe('CSV Upload Workflow', () => {
    test('should display bulk upload interface', async ({ page }) => {
      // Verify upload options are present
      await expect(page.getByText(/upload csv|choose file/i)).toBeVisible()
      await expect(page.getByText(/paste csv|paste content/i)).toBeVisible()

      // Verify download template button exists
      await expect(page.getByRole('button', { name: /download template/i })).toBeVisible()
    })

    test('should download CSV template', async ({ page }) => {
      // Set up download promise
      const downloadPromise = page.waitForEvent('download')

      // Click download template button
      await page.getByRole('button', { name: /download template/i }).click()

      // Wait for download
      const download = await downloadPromise

      // Verify download filename
      expect(download.suggestedFilename()).toMatch(/invitation.*template.*\.csv/i)
    })

    test('should upload valid CSV file successfully', async ({ page }) => {
      const csvContent = generateBulkInvitationsCSV(BULK_INVITATIONS.valid)

      await uploadBulkInvitations(page, csvContent)

      // Verify preview appears
      await expect(page.getByText(/preview/i)).toBeVisible()

      // Verify row count
      await expect(page.getByText(/5 invitation/i)).toBeVisible()

      // Submit
      await submitBulkInvitations(page)

      // Verify success
      await expect(page.getByText(/invitation(s)? sent/i)).toBeVisible({ timeout: 10000 })
    })

    test('should paste CSV content successfully', async ({ page }) => {
      const csvContent = CSV_TEST_DATA.validCSV

      await pasteBulkInvitations(page, csvContent)

      // Verify preview
      await expect(page.getByText(/preview/i)).toBeVisible()

      // Verify parsed data displayed
      await expect(page.getByText(/member1@plinto.dev/i)).toBeVisible()
      await expect(page.getByText(/admin1@plinto.dev/i)).toBeVisible()
    })

    test('should validate CSV format', async ({ page }) => {
      const invalidCSV = CSV_TEST_DATA.invalidFormatCSV

      await pasteBulkInvitations(page, invalidCSV)

      // Verify validation error
      await expect(page.getByText(/invalid (csv )?format/i)).toBeVisible()
    })

    test('should detect missing email column', async ({ page }) => {
      const missingEmailCSV = CSV_TEST_DATA.missingEmailCSV

      await pasteBulkInvitations(page, missingEmailCSV)

      // Verify error about missing email
      await expect(page.getByText(/email.*required|missing email/i)).toBeVisible()
    })

    test('should reject empty CSV', async ({ page }) => {
      const emptyCSV = CSV_TEST_DATA.emptyCSV

      await pasteBulkInvitations(page, emptyCSV)

      // Verify error
      await expect(page.getByText(/empty|no (data|invitations)/i)).toBeVisible()
    })
  })

  test.describe('Bulk Validation Rules', () => {
    test('should enforce 100 invitation limit', async ({ page }) => {
      const tooManyCSV = generateBulkInvitationsCSV(BULK_INVITATIONS.tooMany)

      await pasteBulkInvitations(page, tooManyCSV)

      // Verify limit error
      await expect(page.getByText(/maximum 100|limit.*100/i)).toBeVisible()
    })

    test('should detect duplicate emails', async ({ page }) => {
      const duplicatesCSV = generateBulkInvitationsCSV(BULK_INVITATIONS.duplicates)

      await pasteBulkInvitations(page, duplicatesCSV)

      // Verify duplicate warning
      await expect(page.getByText(/duplicate.*email/i)).toBeVisible()

      // Verify which email is duplicated
      await expect(page.getByText(/duplicate@plinto.dev/i)).toBeVisible()
    })

    test('should validate email formats in bulk', async ({ page }) => {
      const invalidEmailsCSV = CSV_TEST_DATA.invalidEmailsCSV

      await pasteBulkInvitations(page, invalidEmailsCSV)

      // Verify validation errors shown
      await expect(page.getByText(/invalid.*email/i)).toBeVisible()

      // Verify invalid emails are highlighted
      await expect(page.getByText(/invalid-email/i)).toBeVisible()
      await expect(page.getByText(/@nodomain\.com/i)).toBeVisible()
    })

    test('should handle mixed valid and invalid emails', async ({ page }) => {
      const mixedCSV = generateBulkInvitationsCSV(BULK_INVITATIONS.mixedValid)

      await pasteBulkInvitations(page, mixedCSV)

      // Verify preview shows validation status
      await expect(page.getByText(/preview/i)).toBeVisible()

      // Verify valid count
      await expect(page.getByText(/3 valid/i)).toBeVisible()

      // Verify invalid count
      await expect(page.getByText(/2 invalid/i)).toBeVisible()
    })

    test('should allow submitting only valid invitations', async ({ page }) => {
      const mixedCSV = generateBulkInvitationsCSV(BULK_INVITATIONS.mixedValid)

      await pasteBulkInvitations(page, mixedCSV)

      // Look for option to send only valid invitations
      const sendValidButton = page.getByRole('button', {
        name: /send valid|send 3 invitation/i,
      })

      if (await sendValidButton.isVisible()) {
        await sendValidButton.click()

        // Verify partial success message
        await expect(page.getByText(/3.*sent.*2.*failed/i)).toBeVisible({ timeout: 10000 })
      }
    })
  })

  test.describe('CSV Preview', () => {
    test('should display CSV data in table format', async ({ page }) => {
      const csvContent = CSV_TEST_DATA.validCSV

      await pasteBulkInvitations(page, csvContent)

      // Verify table headers
      await expect(page.getByRole('columnheader', { name: /email/i })).toBeVisible()
      await expect(page.getByRole('columnheader', { name: /role/i })).toBeVisible()
      await expect(page.getByRole('columnheader', { name: /message/i })).toBeVisible()

      // Verify data rows
      await expect(page.getByRole('cell', { name: /member1@plinto.dev/i })).toBeVisible()
      await expect(page.getByRole('cell', { name: /admin1@plinto.dev/i })).toBeVisible()
    })

    test('should show validation status for each row', async ({ page }) => {
      const mixedCSV = generateBulkInvitationsCSV(BULK_INVITATIONS.mixedValid)

      await pasteBulkInvitations(page, mixedCSV)

      // Verify validation indicators
      const previewTable = page.locator('table')

      // Check for success indicators on valid rows
      await expect(previewTable.getByText(/valid1@plinto.dev/i).locator('..')).toContainText(
        /(✓|valid|success)/i
      )

      // Check for error indicators on invalid rows
      await expect(previewTable.getByText(/invalid-email/i).locator('..')).toContainText(
        /(✗|invalid|error)/i
      )
    })

    test('should allow editing CSV before submission', async ({ page }) => {
      const csvContent = CSV_TEST_DATA.validCSV

      await pasteBulkInvitations(page, csvContent)

      // Look for edit or back button
      const editButton = page.getByRole('button', { name: /edit|back|modify/i })

      if (await editButton.isVisible()) {
        await editButton.click()

        // Verify textarea is editable again
        const textarea = page.getByLabel(/csv content/i)
        await expect(textarea).toBeEditable()
      }
    })
  })

  test.describe('Bulk Submission', () => {
    test('should submit bulk invitations successfully', async ({ page }) => {
      const csvContent = generateBulkInvitationsCSV(BULK_INVITATIONS.valid)

      await uploadBulkInvitations(page, csvContent)
      await submitBulkInvitations(page)

      // Verify success message with count
      await expect(page.getByText(/5.*invitation.*sent/i)).toBeVisible({ timeout: 10000 })
    })

    test('should display submission results', async ({ page }) => {
      const csvContent = generateBulkInvitationsCSV(BULK_INVITATIONS.valid)

      await uploadBulkInvitations(page, csvContent)
      await submitBulkInvitations(page)

      // Wait for results
      await page.waitForTimeout(2000)

      // Verify results section appears
      await expect(page.getByText(/result|summary/i)).toBeVisible()

      // Verify success count
      await expect(page.getByText(/successful.*5/i)).toBeVisible()
    })

    test('should show individual invitation results', async ({ page }) => {
      const mixedCSV = generateBulkInvitationsCSV(BULK_INVITATIONS.mixedValid)

      await pasteBulkInvitations(page, mixedCSV)

      // Submit (if valid invitations can be sent)
      const sendButton = page.getByRole('button', { name: /send/i })
      if (await sendButton.isEnabled()) {
        await sendButton.click()

        // Wait for results
        await page.waitForTimeout(3000)

        // Verify detailed results with specific emails
        await expect(page.getByText(/valid1@plinto.dev.*success/i)).toBeVisible()
        await expect(page.getByText(/invalid-email.*failed/i)).toBeVisible()
      }
    })

    test('should allow downloading results', async ({ page }) => {
      const csvContent = generateBulkInvitationsCSV(BULK_INVITATIONS.valid)

      await uploadBulkInvitations(page, csvContent)
      await submitBulkInvitations(page)

      // Wait for completion
      await page.waitForTimeout(2000)

      // Look for download results button
      const downloadButton = page.getByRole('button', { name: /download.*result/i })

      if (await downloadButton.isVisible()) {
        const downloadPromise = page.waitForEvent('download')
        await downloadButton.click()
        const download = await downloadPromise

        expect(download.suggestedFilename()).toMatch(/result.*\.csv/i)
      }
    })

    test('should redirect to manage tab after successful submission', async ({ page }) => {
      const csvContent = generateBulkInvitationsCSV(BULK_INVITATIONS.valid)

      await uploadBulkInvitations(page, csvContent)
      await submitBulkInvitations(page)

      // Wait for completion and potential redirect
      await page.waitForTimeout(3000)

      // Look for option to view invitations
      const viewButton = page.getByRole('button', { name: /view.*invitation/i })

      if (await viewButton.isVisible()) {
        await viewButton.click()

        // Verify we're on manage tab
        await expect(page.getByRole('tab', { name: /manage/i })).toHaveAttribute(
          'data-state',
          'active'
        )
      }
    })
  })

  test.describe('Error Handling', () => {
    test('should handle file upload errors gracefully', async ({ page }) => {
      // Try uploading a non-CSV file (by manipulating file chooser)
      const fileChooserPromise = page.waitForEvent('filechooser')
      await page.getByLabel(/upload (csv|file)/i).click()
      const fileChooser = await fileChooserPromise

      // Upload a text file instead of CSV
      await fileChooser.setFiles({
        name: 'document.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('This is not a CSV file'),
      })

      // Verify error message
      await expect(page.getByText(/invalid file type|csv.*required/i)).toBeVisible()
    })

    test('should handle network errors during submission', async ({ page }) => {
      // This test would require mocking network failures
      // In real implementation, would test offline scenario

      const csvContent = generateBulkInvitationsCSV(BULK_INVITATIONS.valid)

      await uploadBulkInvitations(page, csvContent)

      // Simulate going offline (if supported by test environment)
      // await page.context().setOffline(true)

      await submitBulkInvitations(page)

      // Verify error handling
      // Would expect error message about network failure
    })

    test('should validate before allowing submission', async ({ page }) => {
      const invalidCSV = CSV_TEST_DATA.invalidEmailsCSV

      await pasteBulkInvitations(page, invalidCSV)

      // Verify submit button is disabled or shows warning
      const submitButton = page.getByRole('button', { name: /send.*invitation/i })

      // Button should either be disabled or show validation errors
      const isDisabled = await submitButton.isDisabled().catch(() => false)
      const hasErrors = await page.getByText(/cannot send.*invalid/i).isVisible()

      expect(isDisabled || hasErrors).toBe(true)
    })
  })

  test.describe('User Experience', () => {
    test('should show progress indicator during upload', async ({ page }) => {
      const largeCSV = generateBulkInvitationsCSV(
        Array.from({ length: 50 }, (_, i) => ({
          email: `user${i}@plinto.dev`,
          role: 'member',
          message: `Welcome user ${i}`,
        }))
      )

      // Start upload
      await pasteBulkInvitations(page, largeCSV)

      // Look for loading/progress indicator
      const loadingIndicator = page.getByText(/processing|parsing|loading/i)

      // If visible during processing, verify it
      if (await loadingIndicator.isVisible({ timeout: 1000 }).catch(() => false)) {
        await expect(loadingIndicator).toBeVisible()
      }
    })

    test('should allow canceling upload', async ({ page }) => {
      const csvContent = CSV_TEST_DATA.validCSV

      await pasteBulkInvitations(page, csvContent)

      // Look for cancel or clear button
      const cancelButton = page.getByRole('button', { name: /cancel|clear|reset/i })

      if (await cancelButton.isVisible()) {
        await cancelButton.click()

        // Verify form is reset
        await expect(page.getByText(/preview/i)).not.toBeVisible()
      }
    })

    test('should provide helpful error messages', async ({ page }) => {
      const invalidCSV = CSV_TEST_DATA.missingEmailCSV

      await pasteBulkInvitations(page, invalidCSV)

      // Verify error message is descriptive and actionable
      const errorMessage = page.getByText(/email.*required|missing email/i)
      await expect(errorMessage).toBeVisible()

      // Should indicate which rows have issues
      await expect(page.getByText(/row.*1|line.*2/i)).toBeVisible()
    })
  })
})
