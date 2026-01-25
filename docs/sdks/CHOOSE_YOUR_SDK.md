# Choose Your SDK

> **Find the right Janua SDK for your project** - comparison matrix, use cases, and quick links

## SDK Comparison Matrix

| Feature | [React](/packages/react-sdk/) | [Next.js](/packages/nextjs-sdk/) | [Vue](/packages/vue-sdk/) | [TypeScript](/packages/typescript-sdk/) | [Python](/packages/python-sdk/) | [Go](/packages/go-sdk/) | [Flutter](/packages/flutter-sdk/) | [React Native](/packages/react-native-sdk/) |
|---------|:------:|:-------:|:---:|:----------:|:------:|:--:|:-------:|:------------:|
| **Platform** | Web | Web | Web | Any | Server | Server | Mobile | Mobile |
| **Framework** | React 18+ | Next.js 13+ | Vue 3+ | Any | Python 3.8+ | Go 1.21+ | Flutter 3+ | RN 0.70+ |
| **SSR Support** | Partial | Full | Partial | N/A | N/A | N/A | N/A | N/A |
| **Hooks/Composables** | Yes | Yes | Yes | N/A | N/A | N/A | N/A | Yes |
| **Pre-built Components** | Yes | Yes | Yes | No | No | No | Yes | Yes |
| **Bundle Size** | ~15KB | ~18KB | ~12KB | ~8KB | N/A | N/A | N/A | N/A |
| **TypeScript** | Native | Native | Native | Native | Types | N/A | Dart | Native |

## Choose by Use Case

### Building a Web Application

#### Modern React SPA
**Recommended: [@janua/react-sdk](/packages/react-sdk/)**
- Pre-built authentication components
- React hooks for auth state
- Optimistic updates and caching
- Works with Vite, Create React App, etc.

```bash
npm install @janua/react-sdk @janua/sdk
```

#### Next.js Application (App Router)
**Recommended: [@janua/nextjs-sdk](/packages/nextjs-sdk/)**
- Full SSR/SSG support
- Server Components compatible
- Middleware integration
- Edge runtime support

```bash
npm install @janua/nextjs-sdk
```

#### Vue.js Application
**Recommended: [@janua/vue-sdk](/packages/vue-sdk/)**
- Vue 3 Composition API
- Pinia store integration
- Nuxt.js compatible
- TypeScript support

```bash
npm install @janua/vue-sdk
```

#### Vanilla JavaScript or Other Frameworks
**Recommended: [@janua/typescript-sdk](/packages/typescript-sdk/)**
- Framework-agnostic
- Full TypeScript types
- Works anywhere JavaScript runs
- Smallest bundle size

```bash
npm install @janua/sdk
```

### Building a Backend Service

#### Python API/Worker
**Recommended: [janua-python-sdk](/packages/python-sdk/)**
- Async/await support
- FastAPI/Django integration
- Service-to-service auth
- Token validation utilities

```bash
pip install janua-sdk
```

#### Go Service
**Recommended: [janua-go-sdk](/packages/go-sdk/)**
- Context support
- HTTP middleware
- gRPC interceptors
- Connection pooling

```bash
go get github.com/madfam-org/janua/packages/go-sdk
```

### Building a Mobile App

#### Flutter Application
**Recommended: [@janua/flutter-sdk](/packages/flutter-sdk/)**
- Dart-native implementation
- Secure token storage
- Biometric authentication
- Deep linking support

```yaml
# pubspec.yaml
dependencies:
  janua_flutter: ^0.1.0
```

#### React Native Application
**Recommended: [@janua/react-native-sdk](/packages/react-native-sdk/)**
- Native module integration
- Secure storage (Keychain/Keystore)
- Expo compatible
- React hooks API

```bash
npm install @janua/react-native-sdk
```

## Feature Support by SDK

### Authentication Methods

| Method | React | Next.js | Vue | TS | Python | Go | Flutter | RN |
|--------|:-----:|:-------:|:---:|:--:|:------:|:--:|:-------:|:--:|
| Email/Password | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OAuth (Social) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Magic Link | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Passkeys/WebAuthn | ✅ | ✅ | ✅ | ✅ | N/A | N/A | ✅ | ✅ |
| TOTP (2FA) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SMS OTP | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SAML SSO | ⚙️ | ⚙️ | ⚙️ | ⚙️ | ✅ | ✅ | N/A | N/A |

Legend: ✅ Full support | ⚙️ Partial/redirect-based | N/A Not applicable

### Organization & Multi-Tenancy

| Feature | React | Next.js | Vue | TS | Python | Go | Flutter | RN |
|---------|:-----:|:-------:|:---:|:--:|:------:|:--:|:-------:|:--:|
| Organization CRUD | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Member Management | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Role Management | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invitations | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Org Switcher UI | ✅ | ✅ | ✅ | N/A | N/A | N/A | ✅ | ✅ |

## Quick Start by SDK

### React SDK

```tsx
import { JanuaProvider, useAuth } from '@janua/react-sdk';

function App() {
  return (
    <JanuaProvider appId="your-app-id" publicKey="pk_...">
      <AuthenticatedApp />
    </JanuaProvider>
  );
}

function AuthenticatedApp() {
  const { isAuthenticated, signIn, signOut, user } = useAuth();

  if (!isAuthenticated) {
    return <button onClick={() => signIn()}>Sign In</button>;
  }

  return <div>Welcome, {user.name}!</div>;
}
```

### Next.js SDK (App Router)

```tsx
// app/layout.tsx
import { JanuaProvider } from '@janua/nextjs-sdk';

export default function RootLayout({ children }) {
  return (
    <JanuaProvider>
      {children}
    </JanuaProvider>
  );
}

// app/dashboard/page.tsx
import { auth } from '@janua/nextjs-sdk/server';
import { redirect } from 'next/navigation';

export default async function Dashboard() {
  const session = await auth();
  if (!session) redirect('/login');

  return <div>Welcome, {session.user.name}!</div>;
}
```

### Vue SDK

```vue
<script setup>
import { useAuth } from '@janua/vue-sdk';

const { isAuthenticated, user, signIn, signOut } = useAuth();
</script>

<template>
  <div v-if="isAuthenticated">
    Welcome, {{ user.name }}!
    <button @click="signOut">Sign Out</button>
  </div>
  <button v-else @click="signIn">Sign In</button>
</template>
```

### TypeScript SDK

```typescript
import { JanuaClient } from '@janua/sdk';

const janua = new JanuaClient({
  appId: 'your-app-id',
  publicKey: 'pk_...',
});

// Sign in
const { user, token } = await janua.auth.signIn({
  email: 'user@example.com',
  password: 'password123',
});

// Get current user
const currentUser = await janua.users.me();
```

### Python SDK

```python
from janua import JanuaClient

client = JanuaClient(
    base_url="https://api.janua.dev",
    api_key="sk_...",
)

# Verify a token (server-side)
user = client.auth.verify_token(access_token)

# Get user by ID
user = client.users.get(user_id)

# List organization members
members = client.organizations.list_members(org_id)
```

### Go SDK

```go
import janua "github.com/madfam-org/janua/packages/go-sdk/janua"

client := janua.NewClient(janua.Config{
    BaseURL: "https://api.janua.dev",
    APIKey:  "sk_...",
})

// Sign in a user
auth, err := client.Auth.SignIn(ctx, &janua.SignInRequest{
    Email:    "user@example.com",
    Password: "password123",
})

// Get current user
user, err := client.Users.GetCurrentUser(ctx)
```

## SDK Architecture

All Janua SDKs share a common architecture:

```
┌────────────────────────────────────────────┐
│           Your Application                  │
├────────────────────────────────────────────┤
│   Framework SDK (React, Vue, Next.js, etc) │
│   - Hooks/Composables                      │
│   - Pre-built Components                   │
│   - State Management                       │
├────────────────────────────────────────────┤
│           Core SDK (@janua/sdk)            │
│   - API Client                             │
│   - Token Management                       │
│   - Type Definitions                       │
├────────────────────────────────────────────┤
│              Janua API                      │
│        https://api.janua.dev               │
└────────────────────────────────────────────┘
```

## NPM Registry Configuration

Janua SDKs are published to the MADFAM npm registry:

```bash
# Add to .npmrc
@janua:registry=https://npm.madfam.io
//npm.madfam.io/:_authToken=${NPM_MADFAM_TOKEN}
```

## Related Documentation

- [Error Handling Guide](/docs/guides/ERROR_HANDLING_GUIDE.md) - Error codes and SDK-specific handling patterns
- [Rate Limiting](/docs/api/RATE_LIMITING.md) - API rate limits and best practices
- [API Reference](/apps/api/docs/api/endpoints-reference.md) - Complete API documentation
- [Architecture Overview](/docs/architecture/INDEX.md) - System architecture and ADRs
- [Security Best Practices](/docs/security/SECURITY.md) - Security guidelines
- [Troubleshooting Guide](/docs/guides/TROUBLESHOOTING_GUIDE.md) - Common issues and solutions

## SDK-Specific Documentation

| SDK | README | Complete Guide |
|-----|--------|----------------|
| React | [packages/react-sdk/README.md](/packages/react-sdk/README.md) | [React Guide](/docs/guides/react-sdk-complete-guide.md) |
| Next.js | [packages/nextjs-sdk/README.md](/packages/nextjs-sdk/README.md) | - |
| Vue | [packages/vue-sdk/README.md](/packages/vue-sdk/README.md) | [Vue Guide](/docs/guides/vue-sdk-complete-guide.md) |
| TypeScript | [packages/typescript-sdk/README.md](/packages/typescript-sdk/README.md) | - |
| Python | [packages/python-sdk/README.md](/packages/python-sdk/README.md) | - |
| Go | [packages/go-sdk/README.md](/packages/go-sdk/README.md) | - |
| Flutter | [packages/flutter-sdk/README.md](/packages/flutter-sdk/README.md) | [Flutter Guide](/docs/guides/flutter-sdk-complete-guide.md) |
| React Native | [packages/react-native-sdk/README.md](/packages/react-native-sdk/README.md) | - |

## Need Help?

- **GitHub Issues**: [github.com/madfam-org/janua/issues](https://github.com/madfam-org/janua/issues)
- **Documentation**: [docs.janua.dev](https://docs.janua.dev)
- **Discord**: [discord.gg/janua](https://discord.gg/janua)
