import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test('should load login page', async ({ page }) => {
    await page.goto('http://localhost:3000')
    await expect(page).toHaveTitle(/Plinto/)
  })
})
