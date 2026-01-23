# Error Handling

This document describes the error handling patterns used in the Janua API.

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Permission denied |
| 404 | Not Found - Resource not found |
| 422 | Validation Error - Input validation failed |
| 429 | Rate Limited - Too many requests |
| 500 | Internal Error - Server error |

## Error Response Format

All errors follow this JSON structure:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "errors": []
}
```

## Error Codes Reference

### Authentication Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_ERROR` | 401 | Authentication failed |
| `TOKEN_ERROR` | 401 | Invalid or expired token |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |

### Authorization Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHORIZATION_ERROR` | 403 | Permission denied |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `ORGANIZATION_ACCESS_DENIED` | 403 | No access to this organization |

### Validation Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `BAD_REQUEST` | 400 | Invalid request format |
| `MISSING_REQUIRED_FIELD` | 400 | Required field not provided |

### Resource Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_FOUND_ERROR` | 404 | Resource not found |
| `USER_NOT_FOUND` | 404 | User does not exist |
| `ORGANIZATION_NOT_FOUND` | 404 | Organization does not exist |
| `CONFLICT_ERROR` | 409 | Resource already exists |

### Rate Limiting

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `RATE_LIMIT_ERROR` | 429 | Too many requests |

### SSO Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SSO_AUTHENTICATION_ERROR` | 401 | SAML authentication failed |
| `SSO_VALIDATION_ERROR` | 400 | SSO configuration invalid |
| `SSO_CONFIGURATION_ERROR` | 500 | Provider setup incomplete |
| `SSO_METADATA_ERROR` | 400 | SAML metadata parsing failed |
| `SSO_CERTIFICATE_ERROR` | 400 | Certificate validation failed |

## Handling Errors in SDKs

### TypeScript/JavaScript

```typescript
import { JanuaClient, JanuaError } from '@janua/typescript-sdk';

const client = new JanuaClient({ baseUrl: 'https://api.janua.dev' });

try {
  await client.auth.login({ email, password });
} catch (error) {
  if (error instanceof JanuaError) {
    console.error(`Error ${error.code}: ${error.message}`);
    // Handle specific error codes
    if (error.code === 'INVALID_CREDENTIALS') {
      // Show login failed message
    }
  }
}
```

### Python

```python
from janua import JanuaClient, JanuaError

client = JanuaClient(base_url='https://api.janua.dev')

try:
    client.auth.login(email=email, password=password)
except JanuaError as e:
    print(f"Error {e.code}: {e.message}")
    if e.code == 'INVALID_CREDENTIALS':
        # Handle invalid credentials
        pass
```

## Best Practices

1. **Always check error codes** - Don't rely solely on HTTP status codes
2. **Handle token expiration** - Implement automatic token refresh
3. **Log errors appropriately** - Log server errors, not auth failures
4. **Show user-friendly messages** - Map error codes to localized messages
5. **Implement retry logic** - For 429 and 5xx errors with exponential backoff

For complete error codes, see the [API Reference](./API_REFERENCE.md).
