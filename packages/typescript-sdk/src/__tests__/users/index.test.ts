/**
 * Main test file that imports all users test modules
 * This allows running all users tests together while maintaining modularity
 */

// Import all users test modules
import './users-basic.test';
import './users-avatar.test';
import './users-sessions.test';
import './users-suspension.test';
import './users-profile-helpers.test';

describe('Users Test Suite', () => {
  it('should run all users test modules', () => {
    // This test ensures all modules are imported and executed
    expect(true).toBe(true);
  });
});