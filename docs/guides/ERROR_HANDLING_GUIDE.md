# Error Handling Guide

> **Comprehensive guide** for handling Janua API errors in your applications

## Error Response Format

All Janua API errors follow a consistent format:

```json
{
  "detail": "Human-readable error message",
  "code": "ERROR_CODE",
  "status_code": 400,
  "timestamp": "2024-01-25T12:00:00Z",
  "path": "/api/v1/auth/signin",
  "request_id": "req_abc123"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `detail` | string | Human-readable error description |
| `code` | string | Machine-readable error code |
| `status_code` | number | HTTP status code |
| `timestamp` | string | ISO 8601 timestamp |
| `path` | string | Request path that caused the error |
| `request_id` | string | Unique request identifier for support |

## Error Codes Reference

### Authentication Errors (401)

| Code | Description | Resolution |
|------|-------------|------------|
| `AUTHENTICATION_ERROR` | General authentication failure | Check credentials or token |
| `INVALID_CREDENTIALS` | Wrong email/password | Verify login details |
| `TOKEN_ERROR` | Invalid or malformed token | Get new token via refresh |
| `TOKEN_EXPIRED` | Access token has expired | Use refresh token to get new access token |
| `TOKEN_REVOKED` | Token has been revoked | Re-authenticate |
| `SESSION_EXPIRED` | Session no longer valid | Sign in again |
| `MFA_REQUIRED` | MFA verification needed | Complete MFA challenge |
| `INVALID_MFA_CODE` | Wrong MFA code provided | Verify code and try again |

### Authorization Errors (403)

| Code | Description | Resolution |
|------|-------------|------------|
| `AUTHORIZATION_ERROR` | General authorization failure | Check user permissions |
| `INSUFFICIENT_PERMISSIONS` | Missing required permission | Request elevated access |
| `ROLE_REQUIRED` | Specific role needed | Contact organization admin |
| `ORGANIZATION_ACCESS_DENIED` | Not a member of organization | Request invitation |
| `EMAIL_NOT_VERIFIED` | Email verification required | Check email and verify |
| `ACCOUNT_LOCKED` | Account temporarily locked | Wait or contact support |
| `IP_BANNED` | IP temporarily banned | Wait for ban to expire |

### Validation Errors (400/422)

| Code | Description | Resolution |
|------|-------------|------------|
| `BAD_REQUEST` | Malformed request | Check request format |
| `VALIDATION_ERROR` | Input validation failed | Fix validation errors |
| `INVALID_EMAIL` | Email format invalid | Provide valid email |
| `WEAK_PASSWORD` | Password doesn't meet requirements | Use stronger password |
| `MISSING_FIELD` | Required field missing | Include all required fields |
| `INVALID_FORMAT` | Field format incorrect | Check field format requirements |

### Resource Errors (404/409)

| Code | Description | Resolution |
|------|-------------|------------|
| `NOT_FOUND_ERROR` | Resource not found | Verify resource exists |
| `USER_NOT_FOUND` | User doesn't exist | Check user ID |
| `ORGANIZATION_NOT_FOUND` | Organization doesn't exist | Check organization ID |
| `SESSION_NOT_FOUND` | Session doesn't exist | May have been revoked |
| `CONFLICT_ERROR` | Resource already exists | Use different identifier |
| `EMAIL_ALREADY_EXISTS` | Email already registered | Sign in or use different email |
| `USERNAME_TAKEN` | Username not available | Choose different username |

### Rate Limiting Errors (429)

| Code | Description | Resolution |
|------|-------------|------------|
| `RATE_LIMIT_ERROR` | Too many requests | Wait and retry with backoff |

### Server Errors (500)

| Code | Description | Resolution |
|------|-------------|------------|
| `INTERNAL_ERROR` | Server error occurred | Retry later, contact support if persistent |
| `DATABASE_ERROR` | Database operation failed | Retry later |
| `SERVICE_UNAVAILABLE` | Service temporarily unavailable | Check status page, retry later |

## SDK Error Handling

### TypeScript/JavaScript SDK

```typescript
import { JanuaClient, JanuaError, AuthenticationError, RateLimitError } from '@janua/sdk';

const client = new JanuaClient({ appId: 'your-app-id' });

try {
  const { user, token } = await client.auth.signIn({
    email: 'user@example.com',
    password: 'password123',
  });
} catch (error) {
  if (error instanceof AuthenticationError) {
    // Handle authentication errors
    switch (error.code) {
      case 'INVALID_CREDENTIALS':
        showNotification('Invalid email or password');
        break;
      case 'MFA_REQUIRED':
        // Redirect to MFA verification
        showMFAChallenge(error.mfaChallengeId);
        break;
      case 'EMAIL_NOT_VERIFIED':
        showNotification('Please verify your email first');
        break;
      case 'ACCOUNT_LOCKED':
        showNotification(`Account locked. Try again in ${error.retryAfter} seconds`);
        break;
      default:
        showNotification('Authentication failed');
    }
  } else if (error instanceof RateLimitError) {
    // Handle rate limiting
    showNotification(`Too many requests. Please wait ${error.retryAfter} seconds`);
  } else if (error instanceof JanuaError) {
    // Handle other API errors
    console.error(`API Error: ${error.code} - ${error.message}`);
    showNotification(error.message);
  } else {
    // Handle network or unexpected errors
    console.error('Unexpected error:', error);
    showNotification('Something went wrong. Please try again.');
  }
}
```

### React SDK

```tsx
import { useAuth, useJanuaError } from '@janua/react-sdk';
import { useState } from 'react';

function LoginForm() {
  const { signIn } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [showMFA, setShowMFA] = useState(false);
  const [mfaChallengeId, setMfaChallengeId] = useState<string | null>(null);

  const handleSubmit = async (email: string, password: string) => {
    setError(null);

    try {
      await signIn({ email, password });
      // Success - redirect happens automatically
    } catch (err: any) {
      switch (err.code) {
        case 'INVALID_CREDENTIALS':
          setError('Invalid email or password');
          break;
        case 'MFA_REQUIRED':
          setShowMFA(true);
          setMfaChallengeId(err.mfaChallengeId);
          break;
        case 'EMAIL_NOT_VERIFIED':
          setError('Please verify your email before signing in');
          break;
        case 'ACCOUNT_LOCKED':
          setError(`Account temporarily locked. Try again in ${err.retryAfter} seconds`);
          break;
        case 'RATE_LIMIT_ERROR':
          setError(`Too many attempts. Please wait ${err.retryAfter} seconds`);
          break;
        default:
          setError(err.message || 'Sign in failed');
      }
    }
  };

  if (showMFA) {
    return <MFAVerification challengeId={mfaChallengeId} />;
  }

  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="error">{error}</div>}
      {/* form fields */}
    </form>
  );
}
```

### Python SDK

```python
from janua import JanuaClient
from janua.exceptions import (
    JanuaError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)

client = JanuaClient(api_key="sk_...")

try:
    user = client.auth.sign_in(
        email="user@example.com",
        password="password123"
    )
except AuthenticationError as e:
    if e.code == "INVALID_CREDENTIALS":
        print("Invalid email or password")
    elif e.code == "MFA_REQUIRED":
        # Handle MFA challenge
        challenge_id = e.details.get("mfa_challenge_id")
        handle_mfa(challenge_id)
    elif e.code == "EMAIL_NOT_VERIFIED":
        print("Please verify your email first")
    else:
        print(f"Authentication failed: {e.message}")

except AuthorizationError as e:
    print(f"Access denied: {e.message}")

except ValidationError as e:
    for field_error in e.errors:
        print(f"Validation error on {field_error['field']}: {field_error['message']}")

except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")

except NotFoundError as e:
    print(f"Resource not found: {e.message}")

except JanuaError as e:
    # Catch-all for other API errors
    print(f"API error [{e.code}]: {e.message}")

except Exception as e:
    # Network or unexpected errors
    print(f"Unexpected error: {e}")
```

### Go SDK

```go
import (
    "errors"
    "fmt"
    "log"

    janua "github.com/madfam-org/janua/packages/go-sdk/janua"
)

client := janua.NewClient(janua.Config{
    BaseURL: "https://api.janua.dev",
    APIKey:  "sk_...",
})

resp, err := client.Auth.SignIn(ctx, &janua.SignInRequest{
    Email:    "user@example.com",
    Password: "password123",
})

if err != nil {
    var apiErr *janua.APIError
    if errors.As(err, &apiErr) {
        switch apiErr.Code {
        case "INVALID_CREDENTIALS":
            log.Println("Invalid email or password")
        case "MFA_REQUIRED":
            // Handle MFA challenge
            handleMFA(apiErr.Details["mfa_challenge_id"].(string))
        case "EMAIL_NOT_VERIFIED":
            log.Println("Please verify your email first")
        case "ACCOUNT_LOCKED":
            log.Printf("Account locked. Try again in %d seconds", apiErr.RetryAfter)
        case "RATE_LIMIT_ERROR":
            log.Printf("Rate limited. Retry after %d seconds", apiErr.RetryAfter)
        default:
            log.Printf("API error [%s]: %s", apiErr.Code, apiErr.Message)
        }
        return
    }

    // Network or unexpected error
    log.Printf("Request failed: %v", err)
}
```

## Error Handling Patterns

### Retry with Exponential Backoff

For transient errors and rate limiting:

```typescript
async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  baseDelay = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;

      // Don't retry non-transient errors
      if (!isRetryable(error)) {
        throw error;
      }

      // Calculate delay with exponential backoff
      const delay = error.retryAfter
        ? error.retryAfter * 1000
        : baseDelay * Math.pow(2, attempt);

      // Add jitter to prevent thundering herd
      const jitter = delay * 0.1 * Math.random();

      await sleep(delay + jitter);
    }
  }

  throw lastError!;
}

function isRetryable(error: any): boolean {
  return (
    error.code === 'RATE_LIMIT_ERROR' ||
    error.code === 'SERVICE_UNAVAILABLE' ||
    error.status === 503 ||
    error.status === 429
  );
}
```

### Global Error Handler

```typescript
// React error boundary
class AuthErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    if (error instanceof AuthenticationError) {
      // Token invalid - redirect to login
      window.location.href = '/login';
    } else {
      // Log to error tracking service
      errorTracker.captureException(error, { extra: errorInfo });
    }
  }
}

// Express middleware
app.use((err: any, req: Request, res: Response, next: NextFunction) => {
  if (err instanceof JanuaError) {
    return res.status(err.statusCode).json({
      error: err.code,
      message: err.message,
    });
  }

  // Log unexpected errors
  console.error('Unexpected error:', err);
  res.status(500).json({ error: 'INTERNAL_ERROR' });
});
```

### User-Friendly Error Messages

```typescript
const ERROR_MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: 'The email or password you entered is incorrect.',
  EMAIL_ALREADY_EXISTS: 'An account with this email already exists. Try signing in instead.',
  EMAIL_NOT_VERIFIED: 'Please check your email and click the verification link before signing in.',
  WEAK_PASSWORD: 'Password must be at least 8 characters with uppercase, lowercase, number, and special character.',
  MFA_REQUIRED: 'Please enter your two-factor authentication code.',
  INVALID_MFA_CODE: 'The code you entered is incorrect. Please try again.',
  ACCOUNT_LOCKED: 'Your account has been temporarily locked due to too many failed attempts.',
  RATE_LIMIT_ERROR: 'Too many requests. Please wait a moment and try again.',
  SESSION_EXPIRED: 'Your session has expired. Please sign in again.',
  INTERNAL_ERROR: 'Something went wrong on our end. Please try again later.',
};

function getErrorMessage(error: JanuaError): string {
  return ERROR_MESSAGES[error.code] || error.message || 'An unexpected error occurred.';
}
```

## Debugging Tips

### Include Request ID in Support Tickets

Every error response includes a `request_id`. Include this when contacting support:

```typescript
try {
  await client.auth.signIn({ email, password });
} catch (error: any) {
  if (error.requestId) {
    console.error(`Request ID for support: ${error.requestId}`);
  }
}
```

### Enable Debug Logging

```typescript
// TypeScript SDK
const client = new JanuaClient({
  appId: 'your-app-id',
  debug: true, // Enables detailed logging
});

// Python SDK
import logging
logging.getLogger('janua').setLevel(logging.DEBUG)

// Go SDK
client := janua.NewClient(janua.Config{
    BaseURL: "https://api.janua.dev",
    Debug:   true,
})
```

### Check Response Headers

Rate limit and error context are in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1706198460
X-Request-ID: req_abc123
```

## Related Documentation

- [API Reference](/apps/api/docs/api/endpoints-reference.md)
- [Rate Limiting Guide](/docs/api/RATE_LIMITING.md)
- [SDK Selection Guide](/docs/sdks/CHOOSE_YOUR_SDK.md)
- [Security Best Practices](/docs/security/SECURITY.md)
- [Troubleshooting Guide](/docs/guides/TROUBLESHOOTING_GUIDE.md)
