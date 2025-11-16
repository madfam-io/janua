# Debug Statements Audit Report
Generated: Sat Nov 15 18:48:39 CST 2025

## Summary

- TypeScript/JavaScript console statements:      252
- Python print statements:      343

## Categories

### Test Files (Safe - Keep)
- Test file console statements:       38 (no action needed)

### Documentation Examples (Safe - Keep)
- Documentation example statements:       24 (example code)

### Production Code (Action Needed)

#### TypeScript/JavaScript Files
```
apps/demo/lib/config.ts:78:    console.warn(`Unknown environment: ${envName}, falling back to production`)
apps/landing/app/features/page.tsx:55:console.log('User ID:', result.user.id);
apps/landing/app/features/page.tsx:56:console.log('Access Token:', result.tokens.access_token);
apps/landing/app/features/page.tsx:83:console.log('QR Code URL:', mfaSetup.qr_code);
apps/landing/app/features/page.tsx:86:console.log('Backup Codes:', mfaSetup.backup_codes);
apps/landing/app/docs/quickstart/page.tsx:139:    console.error('Signup error:', error);
apps/landing/app/docs/quickstart/page.tsx:181:    console.error('Login error:', error);
apps/landing/app/docs/quickstart/page.tsx:264:    console.error('MFA enable error:', error);
apps/landing/app/docs/quickstart/page.tsx:359:  console.log('Server running on http://localhost:3000');
apps/landing/components/HeroSection.tsx:82:console.log('QR Code:', mfa.qr_code);
apps/admin/lib/monitoring.ts:27:        console.log('[Admin Monitoring]', metric)
apps/admin/lib/monitoring.ts:41:      console.warn('[Admin Monitoring] Failed to track metric:', error)
apps/admin/lib/monitoring.ts:107:      console.warn('[Admin Monitoring] Failed to get metrics:', error)
apps/docs/app/api-reference/example/page.tsx:111:console.log(data.tokens.access);`
apps/docs/app/api/llms-full.txt/route.ts:23:    console.error('Error serving LLM documentation:', error)
apps/docs/src/components/Feedback/FeedbackWidget.tsx:73:      console.error('Failed to submit feedback:', error);
apps/docs/src/components/Feedback/FeedbackWidget.tsx:256:      console.error('Failed to submit feedback:', error);
apps/docs/src/components/GitHubLink/EditOnGitHub.tsx:154:        console.error('Failed to fetch contributors:', error);
apps/docs/src/components/GitHubLink/EditOnGitHub.tsx:236:        console.error('Failed to fetch last updated date:', error);
apps/dashboard/app/api/auth/login/route.ts:41:    console.error('Login API error:', error)
apps/dashboard/app/api/dashboard/recent-activity/route.ts:45:    console.error('Recent activity API error:', error)
apps/dashboard/app/api/dashboard/stats/route.ts:48:    console.error('Stats API error:', error)
apps/dashboard/app/page.tsx:45:        console.error('Failed to initialize dashboard:', error)
apps/dashboard/components/dashboard/recent-activity.tsx:39:      console.error('Error fetching activities:', err)
apps/dashboard/components/dashboard/stats.tsx:72:      console.error('Error fetching stats:', err)
apps/dashboard/lib/auth.tsx:44:        console.error('Failed to initialize auth:', error)
apps/dashboard/lib/auth.tsx:107:      console.error('Failed to refresh user:', error)
apps/dashboard/lib/monitoring.ts:27:        console.log('[Monitoring]', metric)
apps/dashboard/lib/monitoring.ts:41:      console.warn('[Monitoring] Failed to track metric:', error)
apps/dashboard/lib/monitoring.ts:100:      console.warn('[Monitoring] Failed to get metrics:', error)
```

#### Python Files (Non-Documentation)
```
apps/api/app/core/database.py:11:    print(f"Failed to import settings: {e}")
apps/api/app/core/database.py:67:    print(f"Failed to create database engine: {e}")
apps/api/app/core/database.py:68:    print(f"DATABASE_URL: {getattr(settings, 'DATABASE_URL', 'NOT SET')}")
apps/api/app/security/pen_test_framework.py:729:        print("Usage: python pen_test_framework.py <target_url> [output_file]")
apps/api/app/utils/logger.py:4:Replaces print() statements with proper logging that can be controlled
apps/api/app/main.py:669:                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
apps/api/app/services/invitation_service.py:457:            print(f"Failed to send invitation email: {str(e)}")
apps/api/app/services/distributed_session_manager.py:111:            fingerprint = self._create_session_fingerprint(ip_address, user_agent)
apps/api/app/services/distributed_session_manager.py:277:            current_fingerprint = self._create_session_fingerprint(ip_address, user_agent)
apps/api/app/services/distributed_session_manager.py:537:    def _create_session_fingerprint(
apps/api/app/services/websocket_manager.py:312:            print(f"Error sending to connection {connection_id}: {e}")
apps/api/app/services/websocket_manager.py:471:                        print(f"Connection {connection_id} timed out")
apps/api/app/services/websocket_manager.py:482:                print(f"Heartbeat error for {connection_id}: {e}")
```

## Recommendations

### Immediate Actions

1. **Python Production Code**
   - Replace `print()` with `logger.info()` or `logger.debug()`
   - Use: `from app.utils.logger import create_logger`
   - Example: `logger = create_logger(__name__)`

2. **TypeScript/JavaScript Production Code**
   - Replace `console.log()` with `logger.debug()`
   - Use: `import { createLogger } from '@/utils/logger'`
   - Example: `const logger = createLogger('ComponentName')`

3. **Files to Keep As-Is**
   - Test files (*.test.ts, *.spec.ts)
   - Documentation examples (apps/api/app/docs/, apps/api/app/sdk/)
   - Mock/jest setup files

## Implementation Status

- ✅ Created production-safe logger utilities
  - Python: `apps/api/app/utils/logger.py`
  - TypeScript: `packages/core/src/utils/logger.ts`
- ✅ Replaced WebSocket router print statement
- 🔄 Remaining: ~20 production code statements need manual review

