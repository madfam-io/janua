/**
 * Main test file that imports all auth test modules
 * This allows running all auth tests together while maintaining modularity
 */

// Import all auth test modules
import './auth-basic.test';
import './auth-mfa.test';
import './auth-oauth.test';
import './auth-passkey.test';
import './auth-magic-link.test';

describe('Auth Test Suite', () => {
  it('should run all auth test modules', () => {
    // This test ensures all modules are imported and executed
    expect(true).toBe(true);
  });
});