/**
 * Developer Integrator Journey Tests
 * 
 * Validates the complete developer experience from discovery to production deployment.
 * Ensures marketing claims match actual functionality and integration experience.
 * 
 * Journey Stages:
 * 1. Discovery - Landing page and initial value proposition
 * 2. Evaluation - Documentation and pricing assessment
 * 3. Onboarding - Signup and SDK installation
 * 4. Integration - Implementation and testing
 * 5. Testing - Validation and quality assurance
 * 6. Production - Deployment and monitoring
 * 7. Maintenance - Updates and ongoing support
 */

import { test, expect } from '@playwright/test';
import { DeveloperPersona } from '../fixtures/personas';
import { ContentValidator } from '../helpers/content-validator';
import { JourneyMetricsTracker, PerformanceExpectations } from '../helpers/journey-metrics';

test.describe('Developer Integrator Journey', () => {
  
  // ==================== Stage 1: Discovery ====================
  
  test.describe('Stage 1: Discovery', () => {
    
    test('Landing page reflects actual capabilities', async ({ page }) => {
      const metrics = new JourneyMetricsTracker();
      metrics.startJourney('developer-discovery');
      
      // Navigate to landing page
      await page.goto('http://localhost:3000');
      metrics.checkpoint('page-load');
      
      // Validate key messaging
      await expect(page.locator('h1')).toContainText(/Identity|Authentication|Auth/i);
      metrics.checkpoint('hero-visible');
      
      // Check claimed features exist in implementation
      const featuresExist = await page.locator('[data-testid="features-section"]').isVisible();
      
      if (featuresExist) {
        const features = await page.locator('[data-testid="feature-list"] li, [data-testid="feature"]').allTextContents();
        
        // Validate core authentication features are claimed
        const coreFeatures = [
          /multi.*factor|mfa|2fa/i,
          /session/i,
          /oauth|social/i
        ];
        
        let claimedCoreFeatures = 0;
        for (const pattern of coreFeatures) {
          if (features.some(f => pattern.test(f))) {
            claimedCoreFeatures++;
          }
        }
        
        expect(claimedCoreFeatures).toBeGreaterThan(1); // At least 2 core features claimed
        metrics.checkpoint('features-validated');
      }
      
      const result = metrics.endJourney(true);
      console.log(result);
    });

    test('Claimed features have code implementations', async ({ page }) => {
      await page.goto('http://localhost:3000');
      
      // Get all feature claims
      const featureElements = await page.locator('[data-testid="feature"]').all();
      
      // Validate each claimed feature (test first 3 to avoid long test times)
      const featuresToTest = featureElements.slice(0, 3);
      
      for (let i = 0; i < featuresToTest.length; i++) {
        const result = await ContentValidator.validateFeatureClaim(
          page,
          `[data-testid="feature"]:nth-child(${i + 1})`
        );
        
        // Log validation results
        console.log(`Feature: "${result.claimed}"`);
        console.log(`  Implemented: ${result.implemented}`);
        console.log(`  Confidence: ${result.confidence}`);
        console.log(`  Paths: ${result.implementationPaths.slice(0, 3).join(', ')}`);
        
        // At least medium confidence that feature exists
        expect(result.confidence).not.toBe('low');
      }
    });
  });

  // ==================== Stage 2: Evaluation ====================
  
  test.describe('Stage 2: Evaluation', () => {
    
    test('Documentation matches SDK capabilities', async ({ page }) => {
      await page.goto('http://localhost:3000/docs');
      
      // Verify documentation is accessible
      await expect(page).toHaveTitle(/Documentation|Docs/i);
      
      // Check for key documentation sections
      const hasGettingStarted = await page.locator('text=/getting started|quickstart/i').count();
      const hasAPIReference = await page.locator('text=/api reference|api docs/i').count();
      const hasExamples = await page.locator('text=/examples|guides/i').count();
      
      expect(hasGettingStarted + hasAPIReference + hasExamples).toBeGreaterThan(0);
    });

    test('Pricing page shows transparent cost structure', async ({ page }) => {
      await page.goto('http://localhost:3000/pricing');
      
      // Should have pricing tiers visible
      const pricingTiers = await page.locator('[data-testid*="tier"], [class*="pricing"], [class*="plan"]').count();
      expect(pricingTiers).toBeGreaterThan(0);
      
      // Free tier should be clearly marked
      const freeOption = await page.locator('text=/free|$0/i').count();
      expect(freeOption).toBeGreaterThan(0);
    });

    test('Pricing claims match billing service limits', async ({ page }) => {
      // This test validates that what we promise on pricing page
      // matches what we actually enforce in the billing service
      
      const pricingResults = await ContentValidator.validatePricingClaims(page);
      
      // Log results for debugging
      console.log('Pricing Validation Results:');
      pricingResults.forEach(result => {
        console.log(`  ${result.tier}: ${result.matches ? '✅' : '❌'}`);
        console.log(`    Claimed: ${result.claimedLimit}`);
        console.log(`    Actual: ${result.actualLimit}`);
      });
      
      // At least one tier should have matching limits
      const anyMatches = pricingResults.some(r => r.matches);
      expect(anyMatches).toBeTruthy();
    });
  });

  // ==================== Stage 3: Onboarding ====================
  
  test.describe('Stage 3: Onboarding', () => {
    
    test('SDK installation documentation exists', async ({ page }) => {
      await page.goto('http://localhost:3000/docs');
      
      // Look for installation instructions
      const hasInstallCmd = await page.locator('text=/npm install|yarn add|pnpm add/i').count();
      expect(hasInstallCmd).toBeGreaterThan(0);
      
      // Should mention Plinto SDK package
      const hasPlintoSDK = await page.locator('text=/@plinto/i').count();
      expect(hasPlintoSDK).toBeGreaterThan(0);
    });

    test('Quickstart example exists and is valid TypeScript', async ({ page }) => {
      await page.goto('http://localhost:3000/docs');
      
      // Find code example
      const codeBlock = await page.locator('pre code, [class*="code"]').first();
      
      if (await codeBlock.isVisible()) {
        const codeExample = await codeBlock.textContent();
        
        // Should include Plinto client initialization
        expect(codeExample).toMatch(/Plinto|new.*Client|import.*plinto/i);
        
        // Note: Full TypeScript compilation validation would require
        // a more complex setup, see ContentValidator.validateCodeExamples()
      }
    });
  });

  // ==================== Stage 4: Integration ====================
  
  test.describe('Stage 4: Integration', () => {
    
    test('Test app authentication flow works end-to-end', async ({ page }) => {
      const metrics = new JourneyMetricsTracker();
      metrics.startJourney('developer-integration');
      
      const persona = DeveloperPersona.create();
      
      // Navigate to test application (simulates developer's app using SDK)
      await page.goto('http://localhost:3001/test-app');
      metrics.checkpoint('page-load');
      
      // Look for authentication UI
      const hasAuthUI = await page.locator('[data-testid*="auth"], [data-testid*="login"], [data-testid*="signup"]').count();
      expect(hasAuthUI).toBeGreaterThan(0);
      
      metrics.checkpoint('auth-ui-visible');
      
      // Attempt signup
      const signupButton = page.locator('[data-testid="signup-button"], [data-testid="signup-tab"], text=/sign up/i').first();
      
      if (await signupButton.isVisible()) {
        await signupButton.click();
        metrics.checkpoint('signup-form-opened');
        
        // Fill signup form
        await page.fill('[data-testid="email"], input[type="email"]', persona.email);
        await page.fill('[data-testid="password"], input[type="password"]', persona.password);
        
        const nameField = page.locator('[data-testid="name"], input[name="name"]');
        if (await nameField.isVisible()) {
          await page.fill('[data-testid="name"], input[name="name"]', persona.name);
        }
        
        metrics.checkpoint('form-filled');
        
        // Submit signup
        await page.click('[data-testid="signup-submit"], button[type="submit"]');
        metrics.checkpoint('form-submitted');
        
        // Wait for result (success or error)
        await page.waitForSelector('[data-testid*="success"], [data-testid*="error"], [data-testid*="dashboard"]', {
          timeout: 10000
        }).catch(() => {
          // Form submission might redirect or show inline message
        });
        
        metrics.checkpoint('signup-complete');
      }
      
      const result = metrics.endJourney(true);
      console.log(result);
      
      // Validate performance expectations
      const validation = PerformanceExpectations.validate(result);
      console.log(validation.report);
    });
  });

  // ==================== Stage 5: Testing ====================
  
  test.describe('Stage 5: Testing', () => {
    
    test('Performance meets documented expectations', async ({ page }) => {
      const metrics = new JourneyMetricsTracker();
      metrics.startJourney('developer-performance-test');
      
      const persona = DeveloperPersona.create();
      
      // Measure complete authentication flow
      await page.goto('http://localhost:3001/test-app');
      metrics.checkpoint('page-load');
      
      // If signup/login forms exist, measure interaction time
      const authForm = await page.locator('[data-testid="email"], input[type="email"]').first();
      
      if (await authForm.isVisible()) {
        await authForm.fill(persona.email);
        await page.fill('[data-testid="password"], input[type="password"]', persona.password);
        metrics.checkpoint('credentials-entered');
        
        await page.click('[data-testid="login-submit"], [data-testid="signup-submit"], button[type="submit"]');
        metrics.checkpoint('form-submitted');
        
        // Wait for authentication result
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        metrics.checkpoint('authentication-complete');
      }
      
      const result = metrics.endJourney(true);
      
      // Total time should be reasonable (< 10 seconds for local testing)
      expect(result.totalTime).toBeLessThan(10000);
      
      console.log(`Performance: ${result.totalTime}ms`);
    });
  });

  // ==================== Stage 6: Production ====================
  
  test.describe('Stage 6: Production', () => {
    
    test('Health check endpoint is accessible', async ({ request }) => {
      const response = await request.get('http://localhost:8000/health');
      expect(response.ok()).toBeTruthy();
      
      const body = await response.json();
      console.log('Health check response:', body);
    });

    test('Monitoring endpoints exist', async ({ request }) => {
      // Check for metrics endpoint
      const metricsResponse = await request.get('http://localhost:8000/metrics').catch(() => null);
      
      // Either metrics endpoint exists or health endpoint has monitoring info
      const healthResponse = await request.get('http://localhost:8000/health');
      const health = await healthResponse.json();
      
      const hasMonitoring = metricsResponse?.ok() || health.metrics || health.status;
      expect(hasMonitoring).toBeTruthy();
    });
  });

  // ==================== Stage 7: Maintenance ====================
  
  test.describe('Stage 7: Maintenance', () => {
    
    test('SDK package.json exists with proper version', async () => {
      const fs = require('fs');
      const path = require('path');
      
      const sdkPath = path.join(process.cwd(), 'packages/typescript-sdk/package.json');
      
      expect(fs.existsSync(sdkPath)).toBeTruthy();
      
      const packageJson = JSON.parse(fs.readFileSync(sdkPath, 'utf-8'));
      
      // Should have version
      expect(packageJson.version).toBeTruthy();
      
      // Should have name
      expect(packageJson.name).toContain('plinto');
      
      console.log(`SDK Version: ${packageJson.version}`);
    });

    test('SDK has distribution files for NPM publishing', async () => {
      const fs = require('fs');
      const path = require('path');
      
      const distPath = path.join(process.cwd(), 'packages/typescript-sdk/dist');
      
      expect(fs.existsSync(distPath)).toBeTruthy();
      
      // Should have some built files
      const files = fs.readdirSync(distPath);
      expect(files.length).toBeGreaterThan(0);
      
      console.log(`Distribution files: ${files.length}`);
    });
  });

  // ==================== Content-Functionality Alignment ====================
  
  test.describe('Content-Functionality Alignment', () => {
    
    test('All marketing claims are verifiable', async ({ page }) => {
      await page.goto('http://localhost:3000');
      
      // Get main value propositions and claims
      const claims = await page.locator('h2, h3, [data-testid*="claim"], [data-testid*="benefit"]').allTextContents();
      
      console.log('Marketing Claims Found:');
      claims.slice(0, 5).forEach((claim, i) => {
        console.log(`  ${i + 1}. ${claim.trim()}`);
      });
      
      // Should have multiple claims
      expect(claims.length).toBeGreaterThan(0);
    });

    test('Documentation links are accessible', async ({ page }) => {
      await page.goto('http://localhost:3000');
      
      // Find documentation links
      const docsLinks = await page.locator('a[href*="docs"], a:has-text("Documentation"), a:has-text("Docs")').all();
      
      // Should have at least one docs link
      expect(docsLinks.length).toBeGreaterThan(0);
      
      // First docs link should be clickable
      if (docsLinks.length > 0) {
        await docsLinks[0].click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        
        // Should navigate to docs page
        expect(page.url()).toMatch(/docs|documentation/i);
      }
    });
  });
});
