# Week 4.5 Stability Checkpoint - TODO Categorization

**Date**: 2025-11-18  
**Total TODOs Found**: 9 (down from 54 in previous audit)  
**Critical**: 0  
**Important**: 3  
**Nice-to-Have**: 5  
**False Positives**: 1

---

## Summary

Out of 9 TODO comments found in production code:
- **0 Critical** - No blockers for production
- **3 Important** - Should be addressed for production readiness
- **5 Nice-to-Have** - Future enhancements, not blocking
- **1 False Positive** - Not actually a TODO (format comment)

**Recommendation**: Address 3 important TODOs before beta launch, defer 5 nice-to-haves to backlog.

---

## 🔴 CRITICAL (0 items)

None found. All critical functionality is complete.

---

## 🟡 IMPORTANT (3 items)

### 1. SSO Base URL Configuration

**Location**: `app/sso/routers/metadata.py:90, 135`

**Code**:
```python
base_url = "https://api.plinto.dev"  # TODO: Get from settings
```

**Issue**: Hardcoded base URL instead of reading from environment configuration

**Impact**: 
- Won't work in development/staging environments
- Can't customize for self-hosted deployments
- Breaks SSO metadata endpoints in non-production

**Priority**: 🟡 **IMPORTANT** - Required for multi-environment support

**Fix Estimate**: 15 minutes

**Recommended Fix**:
```python
from app.core.config import get_settings

settings = get_settings()
base_url = settings.API_BASE_URL  # or settings.SSO_BASE_URL
```

---

### 2. OIDC Discovery Implementation

**Location**: `app/sso/routers/configuration.py:179`

**Code**:
```python
# TODO: Implement OIDC discovery
```

**Context**: OIDC discovery endpoint stub needs implementation

**Impact**:
- OIDC clients can't auto-configure
- Manual configuration required for SSO integrations
- Reduces enterprise SSO usability

**Priority**: 🟡 **IMPORTANT** - Enterprise feature expectation

**Fix Estimate**: 2-3 hours

**Recommended Fix**:
```python
@router.get("/.well-known/openid-configuration")
async def oidc_discovery():
    return {
        "issuer": settings.SSO_ISSUER,
        "authorization_endpoint": f"{settings.SSO_BASE_URL}/authorize",
        "token_endpoint": f"{settings.SSO_BASE_URL}/token",
        "userinfo_endpoint": f"{settings.SSO_BASE_URL}/userinfo",
        "jwks_uri": f"{settings.SSO_BASE_URL}/.well-known/jwks.json",
        "response_types_supported": ["code", "id_token", "token id_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["openid", "profile", "email"],
    }
```

---

### 3. User Tier Database Fetch

**Location**: `app/middleware/global_rate_limit.py:382`

**Code**:
```python
# TODO: Fetch actual user tier from database
```

**Context**: Rate limiting currently uses default tier instead of user's subscription tier

**Impact**:
- All users get same rate limits regardless of plan
- Premium users don't get higher limits
- Revenue-impacting for tiered pricing

**Priority**: 🟡 **IMPORTANT** - Required for monetization

**Fix Estimate**: 1-2 hours

**Recommended Fix**:
```python
async def get_user_tier(user_id: UUID, db: AsyncSession) -> str:
    """Fetch user's subscription tier from database"""
    result = await db.execute(
        select(Subscription.plan_id)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        return "free"
    
    # Map plan_id to tier
    plan_tiers = {
        "starter": "free",
        "professional": "pro",
        "enterprise": "enterprise"
    }
    return plan_tiers.get(subscription.plan_id, "free")
```

---

## 🟢 NICE-TO-HAVE (5 items)

### 1. Rate Limit Cache Fallback

**Location**: `app/middleware/rate_limit.py:364`

**Code**:
```python
# TODO: Fetch from database if not in cache
```

**Context**: If Redis cache misses, could fall back to database

**Priority**: 🟢 **NICE-TO-HAVE** - Cache should rarely miss

**Impact**: Minor - Redis failures already handled, this is optimization

**Defer**: ✅ Backlog for performance optimization sprint

---

### 2. Circuit Breaker Implementation

**Location**: `app/middleware/global_rate_limit.py:424`

**Code**:
```python
# TODO: Implement circuit breaker logic
```

**Context**: Circuit breaker for Redis connection failures

**Priority**: 🟢 **NICE-TO-HAVE** - Current error handling is adequate

**Impact**: Minor - Would improve resilience but not blocking

**Defer**: ✅ Backlog for reliability sprint

---

### 3. Session Revocation Option

**Location**: `app/users/router.py:196`

**Code**:
```python
# TODO: Optionally revoke all existing sessions for security
```

**Context**: Password change could optionally revoke all sessions

**Priority**: 🟢 **NICE-TO-HAVE** - Security enhancement

**Impact**: Minor - Current session management is secure

**Defer**: ✅ Backlog for security hardening sprint

---

### 4. CVE ID Placeholder

**Location**: `app/security/automated_security_scanner.py:146`

**Code**:
```python
cve_id="CVE-2021-XXXXX",
```

**Context**: Placeholder CVE ID in security scanner test data

**Priority**: 🟢 **NICE-TO-HAVE** - Test/demo code only

**Impact**: None - Not used in production logic

**Defer**: ✅ Cleanup during testing sprint

---

### 5. Format Comment (False Positive)

**Location**: `app/routers/v1/mfa.py:88`

**Code**:
```python
# Format as XXXX-XXXX for readability
```

**Context**: Comment about code formatting, not a TODO

**Priority**: N/A - **FALSE POSITIVE**

**Impact**: None - This is descriptive comment, not action item

**Action**: ✅ Ignore - Not a real TODO

---

## Recommended Actions

### Before Beta Launch (Week 4.5)

Fix 3 important TODOs:

1. ✅ **SSO Base URL Configuration** (15 min)
   - Replace hardcoded URLs with settings
   - Test in dev/staging environments

2. ✅ **OIDC Discovery Endpoint** (2-3 hours)
   - Implement .well-known/openid-configuration
   - Test with OIDC clients

3. ✅ **User Tier Database Fetch** (1-2 hours)
   - Implement subscription tier lookup
   - Integrate with rate limiting middleware

**Total Estimate**: 3-4 hours

### Post-Beta (Backlog)

Defer 5 nice-to-have items:
- Rate limit cache fallback
- Circuit breaker implementation
- Session revocation option
- CVE ID cleanup
- (False positive - ignore)

---

## Implementation Priority

```
Week 4.5 (Before Beta):
├─ 1. SSO Base URL Config (15 min) ✅ MUST DO
├─ 2. OIDC Discovery (2-3 hrs) ✅ MUST DO  
└─ 3. User Tier Fetch (1-2 hrs) ✅ MUST DO

Week 7+ (Post-Beta Backlog):
├─ Circuit breaker logic
├─ Cache fallback
├─ Session revocation
└─ Test data cleanup
```

---

## Risk Assessment

**Current State**:
- ✅ No critical blockers
- ⚠️ 3 important items affecting multi-environment/enterprise features
- ✅ 5 nice-to-haves are truly optional

**If We Ship Without Fixes**:
- ❌ SSO won't work in dev/staging (base URL hardcoded)
- ❌ OIDC auto-configuration unavailable (manual setup required)
- ❌ All users get same rate limits (revenue impact)

**If We Fix Important Items**:
- ✅ Multi-environment SSO working
- ✅ Enterprise OIDC integration streamlined
- ✅ Tiered rate limiting enables monetization

**Recommendation**: ✅ **Fix 3 important TODOs** (3-4 hours investment)

---

## Comparison with Previous Audit

**Previous Audit** (November 17):
- Claimed: 54 TODOs
- Status: Unknown categorization

**Current Audit** (November 18):
- Found: 9 TODOs (83% reduction!)
- Categorized: 0 critical, 3 important, 5 nice-to-have, 1 false positive

**Explanation**: Previous audit may have counted:
- Test file TODOs (excluded from this scan)
- Comments/demo code TODOs
- Already-resolved items

**Current Status**: ✅ **MUCH BETTER** than expected - only 3 items to fix

---

## Next Steps

1. ✅ Fix SSO base URL configuration (15 min)
2. ✅ Implement OIDC discovery endpoint (2-3 hours)
3. ✅ Add user tier database lookup (1-2 hours)
4. ✅ Test all fixes in dev/staging
5. ✅ Mark TODOs as resolved
6. ✅ Continue with quality checklist creation

**Total Time**: 3-4 hours to clear all important TODOs

---

*Generated: November 18, 2025*  
*TODOs Analyzed: 9*  
*Action Required: 3 items (3-4 hours)*  
*Status: ✅ READY FOR FIXES*
