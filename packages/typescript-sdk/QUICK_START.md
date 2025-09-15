# Plinto TypeScript SDK Quick Start

> **Get started with Plinto authentication in your TypeScript/JavaScript application in 5 minutes**

## Installation

```bash
npm install @plinto/typescript-sdk
# or
yarn add @plinto/typescript-sdk
# or
pnpm add @plinto/typescript-sdk
```

## Basic Setup

### 1. Initialize the Client

```typescript
import { PlintoClient } from '@plinto/typescript-sdk';

const plinto = new PlintoClient({
  baseUrl: 'https://plinto.dev',
  tenantId: 'your-tenant-id', // Get from Plinto Dashboard
});
```

### 2. Authentication

#### Sign Up

```typescript
// Email + Password
const { user, session } = await plinto.auth.signUp({
  email: 'user@example.com',
  password: 'SecurePassword123!',
  firstName: 'John',
  lastName: 'Doe',
});

// With additional metadata
const { user, session } = await plinto.auth.signUp({
  email: 'user@example.com',
  password: 'SecurePassword123!',
  metadata: {
    plan: 'premium',
    referralSource: 'google',
  },
});
```

#### Sign In

```typescript
// Email + Password
const { session, user } = await plinto.auth.signIn({
  email: 'user@example.com',
  password: 'SecurePassword123!',
});

// Access tokens
console.log(session.accessToken);
console.log(session.refreshToken);
console.log(session.expiresAt);
```

#### Sign Out

```typescript
await plinto.auth.signOut();
```

### 3. Session Management

#### Get Current Session

```typescript
const session = await plinto.auth.getSession();

if (session) {
  console.log('User is authenticated:', session.userId);
} else {
  console.log('User is not authenticated');
}
```

#### Refresh Token

```typescript
// Automatic refresh
plinto.auth.enableAutoRefresh(); // Refreshes before expiry

// Manual refresh
const newSession = await plinto.auth.refreshSession();
```

#### Verify Token

```typescript
const isValid = await plinto.auth.verifyToken(token);

// With claims extraction
const claims = await plinto.auth.decodeToken(token);
console.log(claims.sub); // User ID
console.log(claims.tid); // Tenant ID
console.log(claims.exp); // Expiration
```

### 4. User Management

#### Get Current User

```typescript
const user = await plinto.users.getCurrentUser();
console.log(user.email);
console.log(user.profile);
```

#### Update Profile

```typescript
const updatedUser = await plinto.users.updateProfile({
  firstName: 'Jane',
  lastName: 'Smith',
  phoneNumber: '+1234567890',
  metadata: {
    timezone: 'America/New_York',
  },
});
```

#### Change Password

```typescript
await plinto.users.changePassword({
  currentPassword: 'OldPassword123!',
  newPassword: 'NewPassword456!',
});
```

### 5. Passkeys (WebAuthn)

#### Register Passkey

```typescript
// Start registration
const options = await plinto.passkeys.startRegistration();

// Use browser WebAuthn API
const credential = await navigator.credentials.create(options);

// Complete registration
await plinto.passkeys.completeRegistration(credential);
```

#### Authenticate with Passkey

```typescript
// Start authentication
const options = await plinto.passkeys.startAuthentication();

// Use browser WebAuthn API
const credential = await navigator.credentials.get(options);

// Complete authentication
const { session } = await plinto.passkeys.completeAuthentication(credential);
```

### 6. Multi-Factor Authentication

#### Enable TOTP

```typescript
// Get QR code and secret
const { qrCode, secret } = await plinto.mfa.enableTotp();

// Display QR code to user
// User scans with authenticator app

// Verify TOTP code
await plinto.mfa.verifyTotp({
  code: '123456', // Code from authenticator app
});
```

#### Verify MFA During Sign In

```typescript
try {
  const { session } = await plinto.auth.signIn({
    email: 'user@example.com',
    password: 'password',
  });
} catch (error) {
  if (error.code === 'MFA_REQUIRED') {
    // Prompt for MFA code
    const { session } = await plinto.auth.verifyMfa({
      code: '123456',
      challengeId: error.challengeId,
    });
  }
}
```

### 7. Organizations

#### Create Organization

```typescript
const org = await plinto.organizations.create({
  name: 'Acme Corp',
  slug: 'acme-corp',
  metadata: {
    industry: 'technology',
    size: '50-100',
  },
});
```

#### Invite Members

```typescript
await plinto.organizations.inviteMembers(orgId, [
  {
    email: 'colleague@example.com',
    role: 'member',
  },
  {
    email: 'admin@example.com',
    role: 'admin',
  },
]);
```

#### Switch Organization Context

```typescript
// List user's organizations
const orgs = await plinto.organizations.list();

// Switch active organization
await plinto.organizations.switchTo(orgId);

// All subsequent API calls use this org context
```

### 8. Webhooks

#### Verify Webhook Signature

```typescript
import { verifyWebhookSignature } from '@plinto/typescript-sdk';

// In your webhook endpoint
export async function handleWebhook(req: Request) {
  const signature = req.headers['x-plinto-signature'];
  const body = await req.text();

  const isValid = verifyWebhookSignature(
    body,
    signature,
    process.env.WEBHOOK_SECRET
  );

  if (!isValid) {
    return new Response('Invalid signature', { status: 401 });
  }

  const event = JSON.parse(body);
  
  switch (event.type) {
    case 'user.created':
      console.log('New user:', event.data);
      break;
    case 'user.updated':
      console.log('User updated:', event.data);
      break;
    // Handle other events
  }

  return new Response('OK', { status: 200 });
}
```

## Advanced Usage

### Custom Request Headers

```typescript
const plinto = new PlintoClient({
  baseUrl: 'https://plinto.dev',
  tenantId: 'your-tenant-id',
  headers: {
    'X-Custom-Header': 'value',
  },
});
```

### Request Interceptors

```typescript
// Add request interceptor
plinto.interceptors.request.use((config) => {
  console.log('Request:', config);
  return config;
});

// Add response interceptor
plinto.interceptors.response.use(
  (response) => {
    console.log('Response:', response);
    return response;
  },
  (error) => {
    console.error('Error:', error);
    throw error;
  }
);
```

### Error Handling

```typescript
import { PlintoError } from '@plinto/typescript-sdk';

try {
  await plinto.auth.signIn({
    email: 'user@example.com',
    password: 'wrong-password',
  });
} catch (error) {
  if (error instanceof PlintoError) {
    switch (error.code) {
      case 'INVALID_CREDENTIALS':
        console.error('Wrong email or password');
        break;
      case 'USER_LOCKED':
        console.error('Account is locked');
        break;
      case 'MFA_REQUIRED':
        console.log('MFA needed:', error.challengeId);
        break;
      default:
        console.error('Auth error:', error.message);
    }
  }
}
```

### TypeScript Support

The SDK is fully typed with TypeScript:

```typescript
import type {
  User,
  Session,
  Organization,
  SignInOptions,
  SignUpOptions,
  UpdateProfileOptions,
} from '@plinto/typescript-sdk';

// All methods have full type support
const signIn = async (options: SignInOptions): Promise<Session> => {
  return await plinto.auth.signIn(options);
};
```

## Framework Integration

### Next.js

See [@plinto/nextjs](../react/README.md) for Next.js specific integration with middleware and server components support.

### Express

```typescript
import express from 'express';
import { PlintoClient } from '@plinto/typescript-sdk';

const app = express();
const plinto = new PlintoClient({
  baseUrl: process.env.PLINTO_URL,
  tenantId: process.env.PLINTO_TENANT_ID,
});

// Middleware to verify tokens
const authenticate = async (req, res, next) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }

  try {
    const claims = await plinto.auth.verifyToken(token);
    req.user = claims;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// Protected route
app.get('/api/profile', authenticate, (req, res) => {
  res.json({ userId: req.user.sub });
});
```

## Best Practices

### 1. Environment Variables

```env
PLINTO_BASE_URL=https://plinto.dev
PLINTO_TENANT_ID=tenant_xxx
PLINTO_WEBHOOK_SECRET=whsec_xxx
```

```typescript
const plinto = new PlintoClient({
  baseUrl: process.env.PLINTO_BASE_URL!,
  tenantId: process.env.PLINTO_TENANT_ID!,
});
```

### 2. Token Storage

- **Never store tokens in localStorage** (XSS vulnerable)
- Use httpOnly cookies for web applications
- Use secure storage for mobile apps
- Implement token refresh before expiry

### 3. Error Recovery

```typescript
const signInWithRetry = async (credentials, maxRetries = 3) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await plinto.auth.signIn(credentials);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      
      // Wait before retry with exponential backoff
      await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
    }
  }
};
```

### 4. Security

- Always use HTTPS in production
- Validate all inputs before sending to API
- Implement rate limiting on sensitive endpoints
- Use CSP headers to prevent XSS
- Enable MFA for sensitive accounts

## Troubleshooting

### Common Issues

**CORS Errors**: Ensure your domain is allowlisted in Plinto dashboard

**Token Expired**: Implement auto-refresh or handle 401 responses

**Network Errors**: Add retry logic with exponential backoff

**Invalid Tenant**: Verify tenant ID in dashboard settings

## API Reference

For complete API documentation, see [API Reference](../../docs/reference/API_SPECIFICATION.md)

## Support

- **Documentation**: [docs.plinto.dev](https://docs.plinto.dev)
- **GitHub Issues**: [github.com/plinto/sdk-js](https://github.com/plinto/sdk-js)
- **Discord**: [discord.gg/plinto](https://discord.gg/plinto)
- **Email**: sdk-support@plinto.dev

## License

MIT - See [LICENSE](./LICENSE) for details