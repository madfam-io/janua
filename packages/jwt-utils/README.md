# @plinto/jwt-utils

JWT and JWKS utilities for the Plinto Identity Platform.

## Installation

```bash
npm install @plinto/jwt-utils
# or
yarn add @plinto/jwt-utils
```

## Features

- JWT token verification
- JWKS cache management
- Token validation utilities
- Type-safe token handling

## Usage

### Verify JWT Token

```typescript
import { verifyToken } from '@plinto/jwt-utils';

const payload = await verifyToken(token, jwks, {
  audience: 'your-app',
  issuer: 'https://plinto.dev'
});
```

### JWKS Cache

```typescript
import { JWKSCache } from '@plinto/jwt-utils';

const cache = new JWKSCache('https://plinto.dev/.well-known/jwks.json');
const jwks = await cache.get();
```

## API Reference

### `verifyToken(token: string, jwks: JWKS, options: VerifyOptions): Promise<JWTPayload>`

Verifies a JWT token against a JWKS.

**Parameters:**
- `token`: The JWT token to verify
- `jwks`: The JSON Web Key Set
- `options`: Verification options (audience, issuer, etc.)

**Returns:** The decoded JWT payload

### `JWKSCache`

Manages caching of JWKS with automatic refresh.

**Methods:**
- `get(): Promise<JWKS>` - Get cached or fetch fresh JWKS
- `refresh(): Promise<JWKS>` - Force refresh of JWKS

## License

MIT