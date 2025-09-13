# TypeScript SDK Quickstart

Get started with Plinto authentication in your TypeScript application with full type safety.

## Installation

```bash
npm install @plinto/typescript-sdk
# or
yarn add @plinto/typescript-sdk
```

## Basic Setup

```typescript
import { PlintoClient, PlintoConfig } from '@plinto/typescript-sdk';

// Configure with type safety
const config: PlintoConfig = {
  baseURL: 'https://api.plinto.dev',
  tenantId: 'YOUR_TENANT_ID',
  clientId: 'YOUR_CLIENT_ID',
};

// Initialize the client
const plinto = new PlintoClient(config);
```

## Type Definitions

```typescript
import type { 
  User, 
  Organization, 
  Session,
  SignUpRequest,
  SignInRequest,
  AuthResponse 
} from '@plinto/typescript-sdk';
```

## Quick Examples

### Sign Up with Type Safety
```typescript
import { SignUpRequest, AuthResponse, PlintoError } from '@plinto/typescript-sdk';

const signUpData: SignUpRequest = {
  email: 'user@example.com',
  password: 'SecurePassword123!',
  firstName: 'John',
  lastName: 'Doe',
  metadata: {
    source: 'web',
    referrer: 'landing-page'
  }
};

try {
  const response: AuthResponse = await plinto.auth.signUp(signUpData);
  console.log('User created:', response.user.id);
} catch (error) {
  if (error instanceof PlintoError) {
    console.error(`Error ${error.code}:`, error.message);
  }
}
```

### Sign In with MFA
```typescript
interface MFASignInFlow {
  email: string;
  password: string;
  mfaCode?: string;
}

async function signInWithMFA({ email, password, mfaCode }: MFASignInFlow): Promise<User> {
  try {
    // Initial sign in
    const response = await plinto.auth.signIn({ email, password });
    
    if (response.requiresMFA) {
      // MFA required
      if (!mfaCode) {
        throw new Error('MFA code required');
      }
      
      const mfaResponse = await plinto.auth.verifyMFA(
        mfaCode, 
        response.challengeId
      );
      return mfaResponse.user;
    }
    
    return response.user;
  } catch (error) {
    if (error instanceof PlintoError) {
      throw error;
    }
    throw new Error('Sign in failed');
  }
}
```

## Generic Types and Utilities

### Paginated Results
```typescript
import { Paginated, ListOptions } from '@plinto/typescript-sdk';

const options: ListOptions = {
  page: 1,
  perPage: 20,
  sort: 'created_at',
  order: 'desc'
};

const users: Paginated<User> = await plinto.users.list(options);
console.log(`Total users: ${users.total}`);
console.log(`Page ${users.page} of ${users.totalPages}`);
```

### Custom Error Handling
```typescript
import { 
  PlintoError, 
  ValidationError, 
  AuthenticationError,
  RateLimitError 
} from '@plinto/typescript-sdk';

function handlePlintoError(error: unknown): void {
  if (error instanceof ValidationError) {
    // Type-safe access to violations
    error.violations?.forEach(violation => {
      console.error(`${violation.field}: ${violation.message}`);
    });
  } else if (error instanceof AuthenticationError) {
    console.error('Authentication failed:', error.message);
    // Redirect to login
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited. Retry after: ${error.retryAfter}s`);
  } else if (error instanceof PlintoError) {
    console.error(`API Error [${error.code}]: ${error.message}`);
  } else {
    console.error('Unexpected error:', error);
  }
}
```

## Advanced TypeScript Features

### Discriminated Unions
```typescript
type AuthState = 
  | { status: 'unauthenticated' }
  | { status: 'authenticating' }
  | { status: 'authenticated'; user: User }
  | { status: 'error'; error: PlintoError };

function handleAuthState(state: AuthState) {
  switch (state.status) {
    case 'authenticated':
      // TypeScript knows `user` exists here
      console.log('Welcome,', state.user.firstName);
      break;
    case 'error':
      // TypeScript knows `error` exists here
      console.error('Auth error:', state.error.message);
      break;
    // ...
  }
}
```

### Utility Types
```typescript
import { DeepPartial, RequireAtLeastOne } from '@plinto/typescript-sdk';

// Partial update types
type UserUpdate = DeepPartial<User>;

// Require at least one field
type SearchCriteria = RequireAtLeastOne<{
  email?: string;
  phone?: string;
  userId?: string;
}>;
```

### Type Guards
```typescript
import { isUser, isOrganization, isPlintoError } from '@plinto/typescript-sdk';

function processEntity(entity: unknown) {
  if (isUser(entity)) {
    // entity is typed as User
    console.log('User email:', entity.email);
  } else if (isOrganization(entity)) {
    // entity is typed as Organization
    console.log('Org name:', entity.name);
  } else if (isPlintoError(entity)) {
    // entity is typed as PlintoError
    console.error('Error:', entity.message);
  }
}
```

## React Integration

### Custom Hook
```typescript
import { useState, useEffect } from 'react';
import { PlintoClient, User, PlintoError } from '@plinto/typescript-sdk';

export function usePlinto() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<PlintoError | null>(null);
  
  const plinto = new PlintoClient({
    baseURL: process.env.REACT_APP_PLINTO_URL!,
    tenantId: process.env.REACT_APP_TENANT_ID!,
    clientId: process.env.REACT_APP_CLIENT_ID!,
  });
  
  useEffect(() => {
    plinto.users.getCurrentUser()
      .then(setUser)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);
  
  return {
    user,
    loading,
    error,
    signIn: plinto.auth.signIn.bind(plinto.auth),
    signOut: plinto.auth.signOut.bind(plinto.auth),
  };
}
```

### Context Provider
```typescript
import React, { createContext, useContext, ReactNode } from 'react';
import { PlintoClient, User } from '@plinto/typescript-sdk';

interface PlintoContextValue {
  client: PlintoClient;
  user: User | null;
  loading: boolean;
}

const PlintoContext = createContext<PlintoContextValue | undefined>(undefined);

export function PlintoProvider({ children }: { children: ReactNode }) {
  // ... implementation
  return (
    <PlintoContext.Provider value={{ client, user, loading }}>
      {children}
    </PlintoContext.Provider>
  );
}

export function usePlintoContext(): PlintoContextValue {
  const context = useContext(PlintoContext);
  if (!context) {
    throw new Error('usePlintoContext must be used within PlintoProvider');
  }
  return context;
}
```

## Testing

### Mock Types
```typescript
import { MockPlintoClient, createMockUser } from '@plinto/typescript-sdk/testing';

describe('Authentication', () => {
  let client: MockPlintoClient;
  
  beforeEach(() => {
    client = new MockPlintoClient();
  });
  
  it('should sign in user', async () => {
    const mockUser = createMockUser({
      email: 'test@example.com',
      firstName: 'Test'
    });
    
    client.auth.signIn.mockResolvedValue({
      user: mockUser,
      tokens: { accessToken: 'mock-token', refreshToken: 'mock-refresh' }
    });
    
    const result = await client.auth.signIn({
      email: 'test@example.com',
      password: 'password'
    });
    
    expect(result.user).toEqual(mockUser);
  });
});
```

## Environment Configuration

### Type-Safe Config
```typescript
// config.ts
interface AppConfig {
  plinto: {
    baseURL: string;
    tenantId: string;
    clientId: string;
    redirectUri?: string;
  };
}

function loadConfig(): AppConfig {
  const config: AppConfig = {
    plinto: {
      baseURL: process.env.PLINTO_URL || 'https://api.plinto.dev',
      tenantId: process.env.PLINTO_TENANT_ID!,
      clientId: process.env.PLINTO_CLIENT_ID!,
      redirectUri: process.env.PLINTO_REDIRECT_URI,
    }
  };
  
  // Validate required fields
  if (!config.plinto.tenantId || !config.plinto.clientId) {
    throw new Error('Missing required Plinto configuration');
  }
  
  return config;
}

export const config = loadConfig();
```

## API Reference Types

### Complete Type Exports
```typescript
export * from './types/auth';
export * from './types/users';
export * from './types/organizations';
export * from './types/sessions';
export * from './types/errors';
export * from './types/common';
export * from './types/utils';
```

## Next Steps

- [Full TypeScript API Reference](/docs/api/typescript)
- [Type Definitions](/docs/api/types)
- [React Integration Guide](/docs/guides/react)
- [Testing Guide](/docs/guides/testing)

## Support

- 📖 [Documentation](https://docs.plinto.dev)
- 🔧 [TypeScript Examples](https://github.com/plinto/typescript-examples)
- 💬 [Community Forum](https://community.plinto.dev)
- 📧 [Support](mailto:support@plinto.dev)