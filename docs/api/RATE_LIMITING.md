# Rate Limiting

> **API rate limiting configuration, headers, and best practices** for Janua integration

## Overview

Janua implements a sliding window rate limiting algorithm to protect the API from abuse while ensuring fair usage across all tenants. Rate limits are applied at three levels:

1. **IP-based** - Limits requests from individual IP addresses
2. **Endpoint-specific** - Stricter limits on sensitive endpoints
3. **Tenant-based** - Limits based on organization billing plan

## Default Rate Limits

### IP-Based Limits

| Client Type | Requests/Minute | Description |
|-------------|-----------------|-------------|
| Standard | 100 | Default for all clients |
| Internal Network | 200 | `10.x.x.x` and `192.168.x.x` ranges |
| Whitelisted | Unlimited | Configured via `RATE_LIMIT_WHITELIST` |

### Endpoint-Specific Limits

Sensitive endpoints have stricter limits to prevent abuse:

| Endpoint Pattern | Requests/Minute | Rationale |
|------------------|-----------------|-----------|
| `/auth/signin` | 10 | Prevent brute force |
| `/auth/signup` | 5 | Prevent account spam |
| `/auth/password/reset` | 3 | Prevent email bombing |
| `/auth/verify` | 5 | Rate limit verifications |
| `/api/v1/sessions` | 100 | Session operations |
| `/api/v1/identities` | 50 | Identity management |
| `/api/v1/organizations` | 30 | Org operations |
| `/api/v1/webhooks` | 20 | Webhook management |

### Tenant Tier Limits

Organizations have rate limits based on their billing plan:

| Plan | Requests/Minute | Monthly Volume |
|------|-----------------|----------------|
| Community | 100 | ~4.3M |
| Pro | 1,000 | ~43M |
| Scale | 5,000 | ~216M |
| Enterprise | 10,000 | ~432M |

## Rate Limit Headers

Every API response includes rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1706198460
```

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed in window |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when window resets |

### Rate Limit Exceeded Response

When rate limited, the API returns HTTP 429:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 45

{
  "detail": "Rate limit exceeded",
  "code": "RATE_LIMIT_ERROR"
}
```

| Header | Description |
|--------|-------------|
| `Retry-After` | Seconds to wait before retrying |

## Handling Rate Limits in SDKs

### TypeScript/JavaScript

```typescript
import { JanuaClient, RateLimitError } from '@janua/sdk';

const client = new JanuaClient({ appId: 'your-app-id' });

async function makeRequest() {
  try {
    const user = await client.users.me();
    return user;
  } catch (error) {
    if (error instanceof RateLimitError) {
      // Wait and retry
      const retryAfter = error.retryAfter || 60;
      console.log(`Rate limited. Retrying in ${retryAfter}s`);
      await sleep(retryAfter * 1000);
      return makeRequest();
    }
    throw error;
  }
}

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

### React SDK

```tsx
import { useAuth } from '@janua/react-sdk';
import { useState } from 'react';

function LoginForm() {
  const { signIn } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isRateLimited, setIsRateLimited] = useState(false);

  const handleSubmit = async (email: string, password: string) => {
    try {
      await signIn({ email, password });
    } catch (err) {
      if (err.code === 'RATE_LIMIT_ERROR') {
        setIsRateLimited(true);
        setError(`Too many attempts. Please wait ${err.retryAfter} seconds.`);

        // Auto-clear after retry period
        setTimeout(() => {
          setIsRateLimited(false);
          setError(null);
        }, err.retryAfter * 1000);
      } else {
        setError(err.message);
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} disabled={isRateLimited}>
      {error && <div className="error">{error}</div>}
      {/* form fields */}
    </form>
  );
}
```

### Python SDK

```python
from janua import JanuaClient
from janua.exceptions import RateLimitError
import time

client = JanuaClient(api_key="sk_...")

def make_request_with_retry(max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.users.me()
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = e.retry_after or 60
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

# Or use the built-in retry mechanism
client = JanuaClient(
    api_key="sk_...",
    retry_count=3,
    retry_wait=1.0,  # Base wait time in seconds
)
```

### Go SDK

```go
import (
    "errors"
    "time"

    janua "github.com/madfam-org/janua/packages/go-sdk/janua"
)

func makeRequestWithRetry(client *janua.Client, maxRetries int) (*janua.User, error) {
    var lastErr error

    for i := 0; i < maxRetries; i++ {
        user, err := client.Users.GetCurrentUser(ctx)
        if err == nil {
            return user, nil
        }

        var apiErr *janua.APIError
        if errors.As(err, &apiErr) && apiErr.Code == "rate_limited" {
            waitTime := apiErr.RetryAfter
            if waitTime == 0 {
                waitTime = 60
            }
            time.Sleep(time.Duration(waitTime) * time.Second)
            lastErr = err
            continue
        }

        return nil, err
    }

    return nil, lastErr
}
```

## Best Practices

### 1. Implement Exponential Backoff

For retry logic, use exponential backoff to avoid overwhelming the API:

```typescript
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  baseDelay = 1000
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (error.code === 'RATE_LIMIT_ERROR' && i < maxRetries - 1) {
        const delay = Math.min(
          error.retryAfter * 1000 || baseDelay * Math.pow(2, i),
          30000 // Max 30 seconds
        );
        await sleep(delay);
        continue;
      }
      throw error;
    }
  }
  throw new Error('Max retries exceeded');
}
```

### 2. Batch Operations When Possible

Instead of making many individual requests:

```typescript
// Bad - many requests
for (const userId of userIds) {
  await client.users.get(userId);
}

// Good - single batch request
const users = await client.users.list({
  ids: userIds,
  per_page: 100,
});
```

### 3. Cache Responses Appropriately

```typescript
import { LRUCache } from 'lru-cache';

const userCache = new LRUCache<string, User>({
  max: 500,
  ttl: 1000 * 60 * 5, // 5 minutes
});

async function getUser(userId: string): Promise<User> {
  const cached = userCache.get(userId);
  if (cached) return cached;

  const user = await client.users.get(userId);
  userCache.set(userId, user);
  return user;
}
```

### 4. Monitor Rate Limit Headers

Track rate limit usage in your application:

```typescript
client.on('response', (response) => {
  const remaining = parseInt(response.headers['x-ratelimit-remaining']);
  const limit = parseInt(response.headers['x-ratelimit-limit']);

  // Log when approaching limit
  if (remaining < limit * 0.2) {
    console.warn(`Rate limit warning: ${remaining}/${limit} remaining`);
  }
});
```

### 5. Use Webhooks for Real-Time Updates

Instead of polling the API, use webhooks:

```typescript
// Bad - polling every 5 seconds
setInterval(async () => {
  const user = await client.users.me();
  updateUI(user);
}, 5000);

// Good - webhook notification
app.post('/webhooks/janua', async (req, res) => {
  const event = req.body;
  if (event.type === 'user.updated') {
    updateUI(event.data.user);
  }
  res.status(200).send('OK');
});
```

## Auto-Ban Protection

Repeated rate limit violations trigger automatic temporary bans:

| Violations (1 hour) | Action |
|---------------------|--------|
| 1-10 | Standard 429 response |
| 11+ | 1-hour IP ban |

Banned clients receive:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": "IP temporarily banned due to repeated violations",
  "code": "IP_BANNED",
  "banned_until": "2024-01-25T16:00:00Z"
}
```

## Adaptive Rate Limiting

Under high system load, rate limits may be automatically reduced:

| System Load | Rate Limit Multiplier |
|-------------|----------------------|
| Low (<30% CPU) | 1.5x (150%) |
| Normal | 1.0x (100%) |
| High (>60% CPU) | 0.7x (70%) |
| Critical (>80% CPU) | 0.3x (30%) |

## Excluded Endpoints

The following endpoints are excluded from rate limiting:

- `/health` - Health check
- `/ready` - Readiness probe
- `/.well-known/jwks.json` - JWKS endpoint

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RATE_LIMIT_ENABLED` | Enable/disable rate limiting | `true` |
| `RATE_LIMIT_DEFAULT` | Default requests/minute | `100` |
| `RATE_LIMIT_WINDOW` | Window size in seconds | `60` |
| `RATE_LIMIT_WHITELIST` | Comma-separated whitelisted IPs | `""` |
| `TRUSTED_PROXIES` | IPs allowed to set X-Forwarded-For | `""` |

### Enterprise Rate Limit Customization

Enterprise customers can request custom rate limits:

1. Contact support at support@janua.dev
2. Provide use case justification
3. Custom limits applied to organization

## Troubleshooting

### "Rate limit exceeded" on first request

Check if your IP is being rate limited at the infrastructure level (CDN, load balancer).

### Inconsistent rate limit counts

Ensure you're sending the `X-Tenant-ID` header consistently for tenant-based limiting.

### Rate limits not resetting

The sliding window algorithm means limits don't reset at fixed intervals. Old requests "fall off" the window continuously.

## Related Documentation

- [Error Handling Guide](/docs/guides/ERROR_HANDLING_GUIDE.md) - Error codes and handling patterns
- [SDK Selection Guide](/docs/sdks/CHOOSE_YOUR_SDK.md) - Choose the right SDK for your platform
- [API Reference](/apps/api/docs/api/endpoints-reference.md) - Complete API documentation
- [Architecture Overview](/docs/architecture/INDEX.md) - System architecture and ADRs
- [Security Guide](/docs/security/SECURITY.md) - Security best practices
- [Troubleshooting Guide](/docs/guides/TROUBLESHOOTING_GUIDE.md) - Rate limit troubleshooting
