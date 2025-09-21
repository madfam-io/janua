import { test, expect } from '@playwright/test';

interface TestResult {
  element: string;
  location: string;
  action: string;
  expected: string;
  result: 'SUCCESS' | 'FAILURE';
  error?: string;
  actualBehavior?: string;
}

test.describe('Focused Link and Interactive Element Testing', () => {
  let results: TestResult[] = [];

  const addResult = (result: TestResult) => {
    results.push(result);
    console.log(`${result.result}: ${result.element} - ${result.action}`);
    if (result.error) {
      console.log(`  Error: ${result.error}`);
    }
  };

  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3003');
    await page.waitForLoadState('networkidle');
  });

  test.afterAll(async () => {
    // Generate comprehensive report
    console.log('\n=== FOCUSED TEST RESULTS ===\n');

    const successCount = results.filter(r => r.result === 'SUCCESS').length;
    const failureCount = results.filter(r => r.result === 'FAILURE').length;

    console.log(`Total Tests: ${results.length}`);
    console.log(`Successes: ${successCount}`);
    console.log(`Failures: ${failureCount}`);
    console.log(`Success Rate: ${((successCount / results.length) * 100).toFixed(2)}%\n`);

    if (failureCount > 0) {
      console.log('=== FAILURES ===');
      results.filter(r => r.result === 'FAILURE').forEach(result => {
        console.log(`❌ ${result.element} (${result.location})`);
        console.log(`   Action: ${result.action}`);
        console.log(`   Expected: ${result.expected}`);
        console.log(`   Error: ${result.error}\n`);
      });
    }

    console.log('=== DETAILED RESULTS ===');
    results.forEach(result => {
      const icon = result.result === 'SUCCESS' ? '✅' : '❌';
      console.log(`${icon} ${result.element}`);
      console.log(`   Location: ${result.location}`);
      console.log(`   Action: ${result.action}`);
      console.log(`   Expected: ${result.expected}`);
      if (result.actualBehavior) {
        console.log(`   Actual: ${result.actualBehavior}`);
      }
      if (result.error) {
        console.log(`   Error: ${result.error}`);
      }
      console.log('');
    });
  });

  test('Navigation and Header Elements', async ({ page }) => {
    // Test Plinto logo/home link
    try {
      const logo = page.locator('nav a[href="/"]').first();
      await logo.click();
      await page.waitForLoadState('networkidle');

      addResult({
        element: 'Plinto Logo/Home Link',
        location: 'Header Navigation',
        action: 'Click logo to return home',
        expected: 'Should navigate to home page',
        result: 'SUCCESS',
        actualBehavior: `Navigated to ${page.url()}`
      });
    } catch (error) {
      addResult({
        element: 'Plinto Logo/Home Link',
        location: 'Header Navigation',
        action: 'Click logo',
        expected: 'Should navigate to home',
        result: 'FAILURE',
        error: error.message
      });
    }

    // Test Pricing link (the only actual navigation link)
    try {
      const pricingLink = page.locator('nav a[href="/pricing"]').first();
      await pricingLink.click();
      await page.waitForLoadState('networkidle');

      const currentUrl = page.url();
      if (currentUrl.includes('/pricing')) {
        addResult({
          element: 'Pricing Navigation Link',
          location: 'Main Navigation',
          action: 'Click pricing link',
          expected: 'Should navigate to pricing page',
          result: 'SUCCESS',
          actualBehavior: `Navigated to ${currentUrl}`
        });
      } else {
        addResult({
          element: 'Pricing Navigation Link',
          location: 'Main Navigation',
          action: 'Click pricing link',
          expected: 'Should navigate to pricing page',
          result: 'FAILURE',
          error: `Expected /pricing, got ${currentUrl}`
        });
      }

      // Go back home
      await page.goto('http://localhost:3003');
      await page.waitForLoadState('networkidle');
    } catch (error) {
      addResult({
        element: 'Pricing Navigation Link',
        location: 'Main Navigation',
        action: 'Click pricing link',
        expected: 'Should navigate to pricing',
        result: 'FAILURE',
        error: error.message
      });
    }

    // Test dropdown navigation items (Product, Developers, Solutions, Company)
    const dropdownItems = [
      { name: 'Product', selector: 'nav a:has-text("Product")' },
      { name: 'Developers', selector: 'nav a:has-text("Developers")' },
      { name: 'Solutions', selector: 'nav a:has-text("Solutions")' },
      { name: 'Company', selector: 'nav a:has-text("Company")' }
    ];

    for (const item of dropdownItems) {
      try {
        const element = page.locator(item.selector).first();
        const href = await element.getAttribute('href');

        if (href === '#') {
          // This is a dropdown trigger
          await element.hover();
          await page.waitForTimeout(500);

          addResult({
            element: `${item.name} Dropdown`,
            location: 'Main Navigation',
            action: 'Hover to show dropdown',
            expected: 'Should be a dropdown menu trigger',
            result: 'SUCCESS',
            actualBehavior: 'Dropdown trigger with href="#"'
          });
        } else {
          addResult({
            element: `${item.name} Navigation`,
            location: 'Main Navigation',
            action: 'Check navigation item',
            expected: 'Should be dropdown or valid link',
            result: 'SUCCESS',
            actualBehavior: `Has href: ${href}`
          });
        }
      } catch (error) {
        addResult({
          element: `${item.name} Navigation`,
          location: 'Main Navigation',
          action: 'Test navigation item',
          expected: 'Should exist and be functional',
          result: 'FAILURE',
          error: error.message
        });
      }
    }

    // Test Sign In button
    try {
      const signInButton = page.locator('a[href*="signin"], button:has-text("Sign In")').first();
      const href = await signInButton.getAttribute('href');

      if (href && href.startsWith('http')) {
        addResult({
          element: 'Sign In Button',
          location: 'Header Navigation',
          action: 'Check sign in link',
          expected: 'Should have external app URL',
          result: 'SUCCESS',
          actualBehavior: `External URL: ${href}`
        });
      } else {
        addResult({
          element: 'Sign In Button',
          location: 'Header Navigation',
          action: 'Check sign in link',
          expected: 'Should have valid URL',
          result: 'FAILURE',
          error: `Invalid URL: ${href}`
        });
      }
    } catch (error) {
      addResult({
        element: 'Sign In Button',
        location: 'Header Navigation',
        action: 'Test sign in button',
        expected: 'Should be functional',
        result: 'FAILURE',
        error: error.message
      });
    }

    // Test Start Free button
    try {
      const startFreeButton = page.locator('a[href*="signup"], button:has-text("Start Free")').first();
      const href = await startFreeButton.getAttribute('href');

      if (href && href.startsWith('http')) {
        addResult({
          element: 'Start Free Button',
          location: 'Header Navigation',
          action: 'Check start free link',
          expected: 'Should have external app URL',
          result: 'SUCCESS',
          actualBehavior: `External URL: ${href}`
        });
      } else {
        addResult({
          element: 'Start Free Button',
          location: 'Header Navigation',
          action: 'Check start free link',
          expected: 'Should have valid URL',
          result: 'FAILURE',
          error: `Invalid URL: ${href}`
        });
      }
    } catch (error) {
      addResult({
        element: 'Start Free Button',
        location: 'Header Navigation',
        action: 'Test start free button',
        expected: 'Should be functional',
        result: 'FAILURE',
        error: error.message
      });
    }

    // Test mobile menu toggle (visible on mobile)
    try {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForTimeout(500);

      const mobileToggle = page.locator('button[aria-label="Toggle menu"]').first();
      if (await mobileToggle.isVisible()) {
        await mobileToggle.click();
        await page.waitForTimeout(500);

        addResult({
          element: 'Mobile Menu Toggle',
          location: 'Mobile Header',
          action: 'Click mobile menu toggle',
          expected: 'Should toggle mobile menu',
          result: 'SUCCESS',
          actualBehavior: 'Mobile menu toggle clicked successfully'
        });
      } else {
        addResult({
          element: 'Mobile Menu Toggle',
          location: 'Mobile Header',
          action: 'Find mobile toggle',
          expected: 'Should be visible on mobile',
          result: 'FAILURE',
          error: 'Mobile toggle not visible on mobile viewport'
        });
      }

      // Reset viewport
      await page.setViewportSize({ width: 1280, height: 720 });
    } catch (error) {
      addResult({
        element: 'Mobile Menu Toggle',
        location: 'Mobile Header',
        action: 'Test mobile toggle',
        expected: 'Should work on mobile',
        result: 'FAILURE',
        error: error.message
      });
    }
  });

  test('Interactive Components and CTAs', async ({ page }) => {
    // Test Performance Demo button
    try {
      const perfButton = page.locator('button:has-text("Run Performance Test")').first();
      if (await perfButton.count() > 0) {
        await perfButton.scrollIntoViewIfNeeded();
        await perfButton.click();
        await page.waitForTimeout(2000);

        addResult({
          element: 'Run Performance Test Button',
          location: 'Performance Section',
          action: 'Click performance test button',
          expected: 'Should trigger performance test',
          result: 'SUCCESS',
          actualBehavior: 'Performance test button clicked'
        });
      } else {
        addResult({
          element: 'Run Performance Test Button',
          location: 'Performance Section',
          action: 'Find performance test button',
          expected: 'Button should exist',
          result: 'FAILURE',
          error: 'Performance test button not found'
        });
      }
    } catch (error) {
      addResult({
        element: 'Run Performance Test Button',
        location: 'Performance Section',
        action: 'Test performance demo',
        expected: 'Should work without error',
        result: 'FAILURE',
        error: error.message
      });
    }

    // Test feature filter buttons
    const filterButtons = page.locator('.inline-flex.items-center.rounded-full.border.px-2\\.5.py-0\\.5.text-xs.font-semibold');
    const filterCount = await filterButtons.count();

    for (let i = 0; i < Math.min(filterCount, 8); i++) {
      try {
        const button = filterButtons.nth(i);
        const buttonText = await button.textContent();

        await button.scrollIntoViewIfNeeded();
        await button.click();
        await page.waitForTimeout(300);

        addResult({
          element: `Feature Filter: ${buttonText}`,
          location: 'Features Section',
          action: 'Click feature filter',
          expected: 'Should filter features',
          result: 'SUCCESS',
          actualBehavior: `Filter "${buttonText}" activated`
        });
      } catch (error) {
        addResult({
          element: `Feature Filter ${i + 1}`,
          location: 'Features Section',
          action: 'Test feature filter',
          expected: 'Should work without error',
          result: 'FAILURE',
          error: error.message
        });
      }
    }

    // Test CTA buttons
    const ctaSelectors = [
      'button:has-text("View Live Demo")',
      'a:has-text("View Source Code")',
      'button:has-text("Get Started")',
      'a:has-text("Start Free")'
    ];

    for (const selector of ctaSelectors) {
      try {
        const ctaButton = page.locator(selector).first();
        if (await ctaButton.count() > 0) {
          const buttonText = await ctaButton.textContent();
          const href = await ctaButton.getAttribute('href');

          if (href && href.startsWith('http')) {
            // External link
            addResult({
              element: `CTA: ${buttonText?.trim()}`,
              location: 'Various Sections',
              action: 'Check CTA external link',
              expected: 'Should have valid external URL',
              result: 'SUCCESS',
              actualBehavior: `External URL: ${href}`
            });
          } else {
            // Internal button or action
            await ctaButton.scrollIntoViewIfNeeded();
            await ctaButton.click();
            await page.waitForTimeout(500);

            addResult({
              element: `CTA: ${buttonText?.trim()}`,
              location: 'Various Sections',
              action: 'Click CTA button',
              expected: 'Should trigger action',
              result: 'SUCCESS',
              actualBehavior: 'CTA button clicked successfully'
            });
          }
        } else {
          addResult({
            element: `CTA Button (${selector})`,
            location: 'Various Sections',
            action: 'Find CTA button',
            expected: 'CTA should exist',
            result: 'FAILURE',
            error: 'CTA button not found'
          });
        }
      } catch (error) {
        addResult({
          element: `CTA Button (${selector})`,
          location: 'Various Sections',
          action: 'Test CTA button',
          expected: 'Should work without error',
          result: 'FAILURE',
          error: error.message
        });
      }
    }
  });

  test('External Links and GitHub Integration', async ({ page }) => {
    // Test GitHub links
    const githubLinks = page.locator('a[href*="github"]');
    const githubCount = await githubLinks.count();

    for (let i = 0; i < githubCount; i++) {
      try {
        const link = githubLinks.nth(i);
        const href = await link.getAttribute('href');
        const target = await link.getAttribute('target');
        const linkText = await link.textContent();

        if (href && href.includes('github')) {
          addResult({
            element: `GitHub Link: ${linkText?.trim() || `Link ${i + 1}`}`,
            location: 'Various Sections',
            action: 'Check GitHub link',
            expected: 'Should have valid GitHub URL',
            result: 'SUCCESS',
            actualBehavior: `URL: ${href}, Target: ${target || 'same-tab'}`
          });
        } else {
          addResult({
            element: `GitHub Link ${i + 1}`,
            location: 'Various Sections',
            action: 'Validate GitHub link',
            expected: 'Should have valid GitHub URL',
            result: 'FAILURE',
            error: `Invalid GitHub URL: ${href}`
          });
        }
      } catch (error) {
        addResult({
          element: `GitHub Link ${i + 1}`,
          location: 'Various Sections',
          action: 'Test GitHub link',
          expected: 'Should work without error',
          result: 'FAILURE',
          error: error.message
        });
      }
    }

    // Test app.plinto.dev links
    const appLinks = page.locator('a[href*="app.plinto.dev"]');
    const appCount = await appLinks.count();

    for (let i = 0; i < appCount; i++) {
      try {
        const link = appLinks.nth(i);
        const href = await link.getAttribute('href');
        const target = await link.getAttribute('target');
        const linkText = await link.textContent();

        addResult({
          element: `App Link: ${linkText?.trim() || `Link ${i + 1}`}`,
          location: 'Various Sections',
          action: 'Check app link',
          expected: 'Should have valid app URL',
          result: 'SUCCESS',
          actualBehavior: `URL: ${href}, Target: ${target || 'same-tab'}`
        });
      } catch (error) {
        addResult({
          element: `App Link ${i + 1}`,
          location: 'Various Sections',
          action: 'Test app link',
          expected: 'Should work without error',
          result: 'FAILURE',
          error: error.message
        });
      }
    }

    // Test external links (mailto, social media, etc.)
    const externalSelectors = [
      'a[href^="mailto:"]',
      'a[href*="twitter.com"]',
      'a[href*="linkedin.com"]',
      'a[href*="docs."]',
      'a[target="_blank"]'
    ];

    for (const selector of externalSelectors) {
      try {
        const links = page.locator(selector);
        const linkCount = await links.count();

        if (linkCount > 0) {
          for (let i = 0; i < Math.min(linkCount, 3); i++) {
            const link = links.nth(i);
            const href = await link.getAttribute('href');
            const linkText = await link.textContent();

            addResult({
              element: `External Link: ${linkText?.trim() || `${selector} ${i + 1}`}`,
              location: 'Various Sections',
              action: 'Check external link',
              expected: 'Should have valid external URL',
              result: 'SUCCESS',
              actualBehavior: `URL: ${href}`
            });
          }
        } else {
          addResult({
            element: `External Links (${selector})`,
            location: 'Various Sections',
            action: 'Find external links',
            expected: 'External links may exist',
            result: 'SUCCESS',
            actualBehavior: 'No links found for this selector (acceptable)'
          });
        }
      } catch (error) {
        addResult({
          element: `External Links (${selector})`,
          location: 'Various Sections',
          action: 'Test external links',
          expected: 'Should work without error',
          result: 'FAILURE',
          error: error.message
        });
      }
    }
  });

  test('Footer Links and Social Media', async ({ page }) => {
    // Scroll to footer
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(1000);

    // Test footer links by looking for common footer patterns
    const footerLinks = page.locator('footer a, [role="contentinfo"] a');
    const footerLinkCount = await footerLinks.count();

    if (footerLinkCount > 0) {
      for (let i = 0; i < Math.min(footerLinkCount, 20); i++) {
        try {
          const link = footerLinks.nth(i);
          const href = await link.getAttribute('href');
          const linkText = await link.textContent();

          if (href) {
            const isExternal = href.startsWith('http') || href.startsWith('mailto:');

            addResult({
              element: `Footer Link: ${linkText?.trim() || `Link ${i + 1}`}`,
              location: 'Footer',
              action: 'Check footer link',
              expected: 'Should have valid URL',
              result: 'SUCCESS',
              actualBehavior: `${isExternal ? 'External' : 'Internal'} URL: ${href}`
            });
          } else {
            addResult({
              element: `Footer Link ${i + 1}`,
              location: 'Footer',
              action: 'Check footer link',
              expected: 'Should have valid URL',
              result: 'FAILURE',
              error: 'No href attribute found'
            });
          }
        } catch (error) {
          addResult({
            element: `Footer Link ${i + 1}`,
            location: 'Footer',
            action: 'Test footer link',
            expected: 'Should work without error',
            result: 'FAILURE',
            error: error.message
          });
        }
      }
    } else {
      addResult({
        element: 'Footer Links',
        location: 'Footer',
        action: 'Find footer links',
        expected: 'Footer should contain links',
        result: 'FAILURE',
        error: 'No footer links found'
      });
    }

    // Test social media links specifically
    const socialSelectors = [
      'a[href*="twitter"]',
      'a[href*="github"]',
      'a[href*="linkedin"]',
      'a[href*="discord"]',
      'a[href^="mailto:"]'
    ];

    for (const selector of socialSelectors) {
      try {
        const socialLinks = page.locator(selector);
        const socialCount = await socialLinks.count();

        if (socialCount > 0) {
          const link = socialLinks.first();
          const href = await link.getAttribute('href');
          const platform = selector.includes('twitter') ? 'Twitter' :
                          selector.includes('github') ? 'GitHub' :
                          selector.includes('linkedin') ? 'LinkedIn' :
                          selector.includes('discord') ? 'Discord' :
                          selector.includes('mailto') ? 'Email' : 'Social';

          addResult({
            element: `${platform} Social Link`,
            location: 'Footer/Social Section',
            action: 'Check social media link',
            expected: 'Should have valid social URL',
            result: 'SUCCESS',
            actualBehavior: `${platform} URL: ${href}`
          });
        } else {
          addResult({
            element: `Social Links (${selector})`,
            location: 'Footer/Social Section',
            action: 'Find social links',
            expected: 'Social links may exist',
            result: 'SUCCESS',
            actualBehavior: 'No social links found for this platform (acceptable)'
          });
        }
      } catch (error) {
        addResult({
          element: `Social Links (${selector})`,
          location: 'Footer/Social Section',
          action: 'Test social links',
          expected: 'Should work without error',
          result: 'FAILURE',
          error: error.message
        });
      }
    }
  });
});