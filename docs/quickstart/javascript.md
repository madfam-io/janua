# JavaScript SDK Quickstart

Get up and running with Plinto authentication in your JavaScript application in under 5 minutes.

## Installation

```bash
npm install @plinto/js-sdk
# or
yarn add @plinto/js-sdk
```

## Basic Setup

```javascript
import { PlintoClient } from '@plinto/js-sdk';

// Initialize the client
const plinto = new PlintoClient({
  baseURL: 'https://api.plinto.dev',
  tenantId: 'YOUR_TENANT_ID',
  clientId: 'YOUR_CLIENT_ID',
});
```

## Quick Examples

### Sign Up
```javascript
try {
  const { user, tokens } = await plinto.auth.signUp({
    email: 'user@example.com',
    password: 'SecurePassword123!',
    firstName: 'John',
    lastName: 'Doe'
  });
  
  console.log('Welcome,', user.firstName);
  // Tokens are automatically stored
} catch (error) {
  console.error('Sign up failed:', error.message);
}
```

### Sign In
```javascript
try {
  const { user, tokens } = await plinto.auth.signIn({
    email: 'user@example.com',
    password: 'SecurePassword123!'
  });
  
  console.log('Welcome back,', user.firstName);
} catch (error) {
  console.error('Sign in failed:', error.message);
}
```

### Get Current User
```javascript
const user = await plinto.users.getCurrentUser();
console.log('Logged in as:', user.email);
```

### Sign Out
```javascript
await plinto.auth.signOut();
console.log('Signed out successfully');
```

## Social Authentication

### Google Sign-In
```javascript
// Redirect to Google
const authUrl = await plinto.auth.signInWithProvider('google');
window.location.href = authUrl;

// Handle callback (in your callback page)
const params = new URLSearchParams(window.location.search);
const code = params.get('code');
const state = params.get('state');

if (code && state) {
  const { user } = await plinto.auth.handleOAuthCallback(code, state);
  console.log('Signed in with Google:', user.email);
}
```

### GitHub Sign-In
```javascript
const authUrl = await plinto.auth.signInWithProvider('github');
window.location.href = authUrl;
```

## Multi-Factor Authentication

### Enable MFA
```javascript
const { qrCode, recoveryCodes } = await plinto.auth.enableMFA();

// Display QR code for user to scan
console.log('Scan this QR code:', qrCode);
console.log('Save these recovery codes:', recoveryCodes);
```

### Verify MFA
```javascript
const code = prompt('Enter your 6-digit code:');
await plinto.auth.verifyMFA(code);
```

## Session Management

### List Sessions
```javascript
const sessions = await plinto.sessions.listSessions();
sessions.forEach(session => {
  console.log(`Device: ${session.device}, Location: ${session.location}`);
});
```

### Revoke Session
```javascript
await plinto.sessions.revokeSession(sessionId);
```

## Organization Management

### List Organizations
```javascript
const orgs = await plinto.organizations.listOrganizations();
orgs.forEach(org => {
  console.log(`${org.name} - Role: ${org.role}`);
});
```

### Create Organization
```javascript
const org = await plinto.organizations.createOrganization({
  name: 'My Company',
  description: 'A great place to work'
});
```

## Error Handling

```javascript
import { PlintoError, ValidationError, AuthenticationError } from '@plinto/js-sdk';

try {
  await plinto.auth.signIn({ email, password });
} catch (error) {
  if (error instanceof ValidationError) {
    // Handle validation errors
    error.violations.forEach(v => {
      console.error(`${v.field}: ${v.message}`);
    });
  } else if (error instanceof AuthenticationError) {
    // Handle auth errors
    console.error('Invalid credentials');
  } else if (error instanceof PlintoError) {
    // Handle other Plinto errors
    console.error(`Error ${error.code}: ${error.message}`);
  } else {
    // Handle unexpected errors
    console.error('Unexpected error:', error);
  }
}
```

## Advanced Configuration

### Custom Storage
```javascript
const plinto = new PlintoClient({
  baseURL: 'https://api.plinto.dev',
  tenantId: 'YOUR_TENANT_ID',
  clientId: 'YOUR_CLIENT_ID',
  storage: {
    getItem: (key) => customStorage.get(key),
    setItem: (key, value) => customStorage.set(key, value),
    removeItem: (key) => customStorage.delete(key)
  }
});
```

### Custom HTTP Client
```javascript
const plinto = new PlintoClient({
  baseURL: 'https://api.plinto.dev',
  tenantId: 'YOUR_TENANT_ID',
  clientId: 'YOUR_CLIENT_ID',
  httpClient: customAxiosInstance
});
```

## WebAuthn/Passkeys

### Register Passkey
```javascript
const credential = await plinto.auth.registerPasskey();
console.log('Passkey registered successfully');
```

### Sign In with Passkey
```javascript
const { user } = await plinto.auth.signInWithPasskey();
console.log('Signed in with passkey:', user.email);
```

## Best Practices

1. **Token Management**: Tokens are automatically refreshed - no manual handling needed
2. **Error Handling**: Always wrap API calls in try-catch blocks
3. **Security**: Never log or expose tokens in production
4. **Storage**: Use secure storage options in production environments

## Next Steps

- [Full API Reference](/docs/api/javascript)
- [Authentication Guide](/docs/guides/authentication)
- [Security Best Practices](/docs/guides/security)
- [Examples Repository](https://github.com/plinto/examples)

## Support

Need help? 
- 📖 [Documentation](https://docs.plinto.dev)
- 💬 [Community Forum](https://community.plinto.dev)
- 📧 [Support](mailto:support@plinto.dev)