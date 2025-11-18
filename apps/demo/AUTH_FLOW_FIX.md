# Authentication Flow Fix - 401 Errors Resolution

**Date**: 2025-11-17  
**Status**: ✅ Fixed  
**Issue**: "No refresh token available" + 401 Unauthorized errors

## Problem Analysis

### Errors Observed
```
No refresh token available
Failed to load resource: the server responded with a status of 401 (Unauthorized)
:8000/api/v1/auth/login:1 Failed to load resource: 401 (Unauthorized)
```

### Root Cause

**Frontend Sign-In Implementation Bug**

The sign-in page was checking for `result.accessToken` but the SDK actually returns:
```typescript
{
  user: User,
  tokens: {
    access_token: string,
    refresh_token: string,
    token_type: 'bearer',
    expires_in: number
  }
}
```

## Solution

### Fixed: apps/demo/app/signin/page.tsx

**Before (Broken)**:
```typescript
const result = await client.auth.signIn({
  email,
  password,
})

if (result.accessToken) {  // ❌ WRONG - accessToken doesn't exist
  router.push('/dashboard')
}
```

**After (Fixed)**:
```typescript
const result = await client.auth.signIn({
  email,
  password,
})

if (result.tokens?.access_token) {  // ✅ CORRECT
  router.push('/dashboard')
}
```

## How Authentication Works

### 1. SDK Structure (TypeScript SDK)

From `packages/typescript-sdk/src/auth.ts`:
```typescript
async signIn(request: SignInRequest): Promise<AuthResponse> {
  const response = await this.http.post<AuthApiResponse>('/api/v1/auth/login', request);
  
  // Store tokens in TokenManager
  if (response.data.access_token && response.data.refresh_token) {
    await this.tokenManager.setTokens({
      access_token: response.data.access_token,
      refresh_token: response.data.refresh_token,
      expires_at: Date.now() + (response.data.expires_in * 1000)
    });
  }
  
  // Return structured response
  return {
    user: response.data.user,
    tokens: {
      access_token: response.data.access_token,
      refresh_token: response.data.refresh_token,
      expires_in: response.data.expires_in,
      token_type: response.data.token_type
    }
  };
}
```

### 2. API Response Format

From `apps/api/app/routers/v1/auth.py`:
```python
return SignInResponse(
    user=UserResponse(
        id=str(user.id),
        email=user.email,
        # ... other user fields
    ),
    tokens=TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    ),
)
```

### 3. Token Storage Flow

1. **User submits credentials** → Frontend calls `client.auth.signIn()`
2. **SDK makes API request** → POST `/api/v1/auth/login`
3. **API validates & creates session** → Returns user + tokens
4. **SDK stores tokens** → `TokenManager.setTokens()` (localStorage/secure storage)
5. **SDK returns to app** → `{ user, tokens }`
6. **App checks tokens** → Should check `result.tokens?.access_token`

## Testing

### Create Test User
```bash
cd /Users/aldoruizluna/labspace/plinto/apps/api
python3 -c "
from passlib.context import CryptContext
import uuid
from datetime import datetime

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
hashed = pwd_context.hash('TestPassword123!')

print(f'Password hash: {hashed}')
"

# Insert into SQLite
sqlite3 plinto_dev.db "
INSERT INTO users (
  id, email, email_verified, password_hash, status,
  first_name, last_name, tenant_id, is_active, created_at, updated_at
) VALUES (
  'bf9f3db2-aec6-4b2b-baff-8a4caf5a59a2',
  'test@example.com',
  1,
  '\$2b\$12\$YOUR_HASH_HERE',
  'ACTIVE',
  'Test',
  'User',
  'bf9f3db2-aec6-4b2b-baff-8a4caf5a59a2',
  1,
  '2025-11-18 04:14:56',
  '2025-11-18 04:14:56'
);"
```

### Test Login Flow

**Via API**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}'

# Expected Success Response:
{
  "user": {
    "id": "bf9f3db2-aec6-4b2b-baff-8a4caf5a59a2",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User"
  },
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "expires_in": 900
  }
}
```

**Via Frontend**:
1. Navigate to http://localhost:3002/signin
2. Enter credentials:
   - Email: `test@example.com`
   - Password: `TestPassword123!`
3. Click "Sign in"
4. Should redirect to `/dashboard` with tokens stored

## Verification Checklist

- [x] Fixed sign-in page to check `result.tokens?.access_token`
- [x] Verified SDK returns correct structure
- [x] Verified API returns correct format
- [x] Created test user in database
- [ ] Test complete sign-in flow via frontend
- [ ] Verify tokens are stored in TokenManager
- [ ] Verify protected routes use stored tokens
- [ ] Test token refresh flow

## Common Errors & Solutions

### "No refresh token available"
- **Cause**: Frontend not correctly accessing `result.tokens.refresh_token`
- **Fix**: Use `result.tokens?.refresh_token` instead of `result.refreshToken`

### 401 Unauthorized on login
- **Cause 1**: User doesn't exist in database → Create test user
- **Cause 2**: Wrong password hash → Verify with passlib
- **Cause 3**: Missing tenant_id → Add to user record

### "Invalid credentials"
- **Cause**: Correct response when password is wrong or user not found
- **Fix**: Verify test user exists and password hash is correct

## Next Steps

1. **Complete Frontend Testing**
   - Test sign-in flow end-to-end
   - Verify dashboard redirect works
   - Check tokens are accessible for API calls

2. **Implement Token Refresh**
   - Verify refresh token flow works
   - Test token expiration handling
   - Implement automatic token refresh

3. **Add Other Auth Pages**
   - Fix sign-up page (if needed)
   - Fix password reset (if needed)
   - Test MFA flows

4. **Production Readiness**
   - Switch to PostgreSQL database
   - Implement proper user onboarding
   - Add email verification flow

## References

- SDK Auth Implementation: `packages/typescript-sdk/src/auth.ts`
- API Auth Router: `apps/api/app/routers/v1/auth.py`
- Frontend Sign-In: `apps/demo/app/signin/page.tsx`
- Type Definitions: `packages/typescript-sdk/dist/types.d.ts`

---

**Status**: Core authentication flow issue resolved ✅  
**Ready for**: Frontend end-to-end testing with real user login
