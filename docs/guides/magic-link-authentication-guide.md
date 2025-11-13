# Magic Link Authentication Implementation Guide

> **Complete guide to passwordless authentication using secure email-based magic links**

## Overview

Plinto API provides passwordless authentication through magic links - secure, time-limited tokens sent via email that allow users to sign in without passwords. This modern authentication method improves user experience while maintaining security.

## 🔗 Magic Link Features

### Core Capabilities
- **Passwordless Authentication**: Sign in without remembering passwords
- **Secure Token Generation**: Cryptographically secure, time-limited tokens
- **Email Integration**: Automated email delivery with customizable templates
- **User Registration**: Automatic account creation for new users
- **Rate Limiting**: Protection against abuse and spam
- **Audit Logging**: Complete tracking of magic link usage

### Security Features
- **Time-limited tokens** (default: 15 minutes expiration)
- **Single-use tokens** (automatically invalidated after use)
- **Rate limiting** (5 requests per hour per email)
- **Secure token generation** using cryptographically random values
- **IP address tracking** for security monitoring
- **Email verification** built into the flow

## 🚀 Quick Start

### 1. Send Magic Link

```bash
curl -X POST "https://api.plinto.dev/api/v1/auth/magic-link" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "redirect_url": "https://myapp.com/auth/callback"
  }'
```

**Response:**
```json
{
  "message": "Magic link sent to your email",
  "expires_in": 900,
  "email_sent": true
}
```

### 2. Verify Magic Link

```bash
curl -X POST "https://api.plinto.dev/api/v1/auth/magic-link/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "123",
      "email": "user@example.com",
      "email_verified": true,
      "created_at": "2025-01-16T10:30:00Z"
    },
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

## 📱 Client Implementation

### Frontend Integration Example

```javascript
class MagicLinkAuth {
  constructor(apiClient) {
    this.api = apiClient;
  }

  // Send magic link
  async sendMagicLink(email, redirectUrl = null) {
    try {
      const response = await this.api.post('/api/v1/auth/magic-link', {
        email,
        redirect_url: redirectUrl
      });

      return {
        success: true,
        message: response.data.message,
        expiresIn: response.data.expires_in
      };
    } catch (error) {
      if (error.response?.status === 429) {
        throw new Error('Too many requests. Please wait before requesting another magic link.');
      }
      throw new Error(`Failed to send magic link: ${error.response?.data?.detail || error.message}`);
    }
  }

  // Verify magic link token
  async verifyMagicLink(token) {
    try {
      const response = await this.api.post('/api/v1/auth/magic-link/verify', {
        token
      });

      // Store tokens for authenticated requests
      const { access_token, refresh_token } = response.data.data;
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);

      return response.data.data;
    } catch (error) {
      throw new Error(`Magic link verification failed: ${error.response?.data?.detail || error.message}`);
    }
  }

  // Extract token from URL (for redirect handling)
  extractTokenFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('token');
  }

  // Complete magic link flow from URL
  async handleMagicLinkCallback() {
    const token = this.extractTokenFromUrl();
    if (!token) {
      throw new Error('No magic link token found in URL');
    }

    return await this.verifyMagicLink(token);
  }
}
```

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

const MagicLinkAuth = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const magicLinkAuth = new MagicLinkAuth(apiClient);

  // Handle magic link callback on page load
  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      handleMagicLinkCallback(token);
    }
  }, [searchParams]);

  const handleMagicLinkCallback = async (token) => {
    setLoading(true);
    try {
      const result = await magicLinkAuth.verifyMagicLink(token);
      // Redirect to dashboard or desired page
      navigate('/dashboard');
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMagicLink = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const redirectUrl = `${window.location.origin}/auth/magic-link`;
      await magicLinkAuth.sendMagicLink(email, redirectUrl);
      setSent(true);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="magic-link-sent">
        <h2>📧 Check Your Email</h2>
        <p>We've sent a magic link to <strong>{email}</strong></p>
        <p>Click the link in your email to sign in. The link expires in 15 minutes.</p>
        <button onClick={() => setSent(false)}>
          Send Another Link
        </button>
      </div>
    );
  }

  return (
    <div className="magic-link-auth">
      <h2>🔗 Sign In with Magic Link</h2>
      <p>Enter your email to receive a secure sign-in link</p>

      <form onSubmit={handleSendMagicLink}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Enter your email"
          required
          disabled={loading}
        />

        <button type="submit" disabled={loading}>
          {loading ? 'Sending...' : 'Send Magic Link'}
        </button>

        {error && <div className="error">{error}</div>}
      </form>

      <div className="alternative-auth">
        <p>Or <a href="/auth/signin">sign in with password</a></p>
      </div>
    </div>
  );
};
```

### Vue.js Component Example

```vue
<template>
  <div class="magic-link-auth">
    <div v-if="!sent">
      <h2>🔗 Sign In with Magic Link</h2>
      <p>Enter your email to receive a secure sign-in link</p>

      <form @submit.prevent="sendMagicLink">
        <input
          v-model="email"
          type="email"
          placeholder="Enter your email"
          required
          :disabled="loading"
        />

        <button type="submit" :disabled="loading">
          {{ loading ? 'Sending...' : 'Send Magic Link' }}
        </button>

        <div v-if="error" class="error">{{ error }}</div>
      </form>
    </div>

    <div v-else class="magic-link-sent">
      <h2>📧 Check Your Email</h2>
      <p>We've sent a magic link to <strong>{{ email }}</strong></p>
      <p>Click the link in your email to sign in. The link expires in 15 minutes.</p>
      <button @click="sent = false">Send Another Link</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const email = ref('');
const loading = ref(false);
const sent = ref(false);
const error = ref('');
const route = useRoute();
const router = useRouter();

const magicLinkAuth = new MagicLinkAuth(apiClient);

// Handle magic link callback
onMounted(() => {
  const token = route.query.token;
  if (token) {
    verifyMagicLink(token);
  }
});

const sendMagicLink = async () => {
  loading.value = true;
  error.value = '';

  try {
    const redirectUrl = `${window.location.origin}/auth/magic-link`;
    await magicLinkAuth.sendMagicLink(email.value, redirectUrl);
    sent.value = true;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
};

const verifyMagicLink = async (token) => {
  loading.value = true;
  try {
    await magicLinkAuth.verifyMagicLink(token);
    router.push('/dashboard');
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
};
</script>
```

## 🔧 Backend Integration

### Email Template Customization

```python
from app.services.email import EmailService

class MagicLinkEmailService:
    def __init__(self):
        self.email_service = EmailService()

    async def send_magic_link_email(
        self,
        email: str,
        magic_link_url: str,
        user_name: str = None,
        redirect_url: str = None
    ):
        """Send customized magic link email"""

        # Custom email template
        template_data = {
            'user_name': user_name or email.split('@')[0],
            'magic_link_url': magic_link_url,
            'app_name': settings.APP_NAME or 'Plinto',
            'expires_minutes': 15,
            'redirect_url': redirect_url
        }

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Your Magic Link</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="padding: 20px; background-color: #f9f9f9;">
                <h1 style="color: #333;">🔗 Your Magic Link</h1>

                <p>Hello {template_data['user_name']},</p>

                <p>Click the button below to sign in to {template_data['app_name']}:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{template_data['magic_link_url']}"
                       style="background-color: #007bff; color: white; padding: 12px 24px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Sign In to {template_data['app_name']}
                    </a>
                </div>

                <p><strong>This link expires in {template_data['expires_minutes']} minutes</strong> and can only be used once.</p>

                <p>If you didn't request this link, you can safely ignore this email.</p>

                <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                <p style="color: #666; font-size: 12px;">
                    For security reasons, don't forward this email or share this link with anyone.
                </p>
            </div>
        </body>
        </html>
        """

        await self.email_service.send_email(
            to_email=email,
            subject=f"Sign in to {template_data['app_name']}",
            html_content=html_content
        )
```

### Custom Redirect Handling

```python
from fastapi import Request
from urllib.parse import urlparse, urljoin

class MagicLinkService:
    def __init__(self):
        self.allowed_redirect_domains = [
            'localhost',
            'myapp.com',
            'staging.myapp.com'
        ]

    def validate_redirect_url(self, redirect_url: str, request: Request) -> str:
        """Validate and sanitize redirect URL"""
        if not redirect_url:
            return None

        try:
            parsed = urlparse(redirect_url)

            # Allow relative URLs
            if not parsed.netloc:
                base_url = f"{request.url.scheme}://{request.url.netloc}"
                return urljoin(base_url, redirect_url)

            # Check against allowed domains
            if parsed.netloc in self.allowed_redirect_domains:
                return redirect_url

            # Fallback to default
            return None

        except Exception:
            return None

    async def create_magic_link_url(
        self,
        token: str,
        redirect_url: str = None,
        request: Request = None
    ) -> str:
        """Create complete magic link URL"""
        base_url = settings.FRONTEND_URL or "https://app.plinto.dev"

        # Validate redirect URL
        safe_redirect = self.validate_redirect_url(redirect_url, request)

        if safe_redirect:
            return f"{safe_redirect}?token={token}"
        else:
            return f"{base_url}/auth/magic-link?token={token}"
```

### Error Handling and Logging

```python
from app.models import ActivityLog
import logging

logger = logging.getLogger(__name__)

class MagicLinkHandler:
    async def handle_magic_link_request(
        self,
        email: str,
        request: Request,
        db: Session
    ):
        """Handle magic link request with comprehensive error handling"""

        try:
            # Log attempt
            await self.log_activity(
                email=email,
                action="magic_link_requested",
                ip_address=request.client.host,
                db=db
            )

            # Check rate limiting
            await self.check_rate_limit(email, request.client.host, db)

            # Generate and send magic link
            magic_link = await self.create_magic_link(email, db)
            await self.send_magic_link_email(email, magic_link)

            # Log success
            await self.log_activity(
                email=email,
                action="magic_link_sent",
                ip_address=request.client.host,
                db=db,
                details={"link_id": magic_link.id}
            )

            return {"message": "Magic link sent", "expires_in": 900}

        except RateLimitExceeded:
            logger.warning(f"Rate limit exceeded for magic link: {email}")
            raise HTTPException(429, "Too many requests")

        except EmailDeliveryError as e:
            logger.error(f"Email delivery failed for {email}: {e}")
            raise HTTPException(500, "Failed to send magic link")

        except Exception as e:
            logger.error(f"Magic link request failed for {email}: {e}")
            raise HTTPException(500, "Magic link request failed")

    async def log_activity(
        self,
        email: str,
        action: str,
        ip_address: str,
        db: Session,
        details: dict = None
    ):
        """Log magic link activity"""
        activity = ActivityLog(
            email=email,
            action=action,
            ip_address=ip_address,
            details=details or {},
            created_at=datetime.utcnow()
        )
        db.add(activity)
        await db.commit()
```

## 🛡️ Security Best Practices

### Rate Limiting Implementation

```python
from datetime import datetime, timedelta
from app.core.cache import redis_client

class MagicLinkRateLimiter:
    def __init__(self):
        self.redis = redis_client
        self.hourly_limit = 5  # 5 magic links per hour
        self.daily_limit = 20  # 20 magic links per day

    async def check_rate_limit(self, email: str, ip_address: str):
        """Check rate limits for magic link requests"""

        # Email-based rate limiting
        email_key_hour = f"magic_link:email:{email}:hour"
        email_key_day = f"magic_link:email:{email}:day"

        # IP-based rate limiting
        ip_key_hour = f"magic_link:ip:{ip_address}:hour"

        # Check limits
        email_hour_count = await self.redis.get(email_key_hour) or 0
        email_day_count = await self.redis.get(email_key_day) or 0
        ip_hour_count = await self.redis.get(ip_key_hour) or 0

        if int(email_hour_count) >= self.hourly_limit:
            raise RateLimitExceeded("Hourly email limit exceeded")

        if int(email_day_count) >= self.daily_limit:
            raise RateLimitExceeded("Daily email limit exceeded")

        if int(ip_hour_count) >= 10:  # IP limit
            raise RateLimitExceeded("IP rate limit exceeded")

        # Increment counters
        await self.redis.incr(email_key_hour)
        await self.redis.expire(email_key_hour, 3600)  # 1 hour

        await self.redis.incr(email_key_day)
        await self.redis.expire(email_key_day, 86400)  # 1 day

        await self.redis.incr(ip_key_hour)
        await self.redis.expire(ip_key_hour, 3600)  # 1 hour
```

### Token Security

```python
import secrets
import hashlib
from cryptography.fernet import Fernet

class SecureMagicLinkToken:
    def __init__(self):
        # Use environment variable for encryption key
        self.cipher = Fernet(settings.MAGIC_LINK_ENCRYPTION_KEY)

    def generate_token(self, user_id: str, email: str) -> str:
        """Generate secure magic link token"""

        # Create payload with user info and timestamp
        timestamp = datetime.utcnow().isoformat()
        payload = f"{user_id}:{email}:{timestamp}:{secrets.token_hex(16)}"

        # Encrypt payload
        encrypted_token = self.cipher.encrypt(payload.encode())

        # Return base64 encoded token
        return encrypted_token.decode()

    def verify_token(self, token: str) -> dict:
        """Verify and decode magic link token"""
        try:
            # Decrypt token
            decrypted = self.cipher.decrypt(token.encode())
            payload = decrypted.decode()

            # Parse payload
            user_id, email, timestamp, nonce = payload.split(':')

            # Check expiration (15 minutes)
            token_time = datetime.fromisoformat(timestamp)
            if datetime.utcnow() - token_time > timedelta(minutes=15):
                raise ValueError("Token expired")

            return {
                "user_id": user_id,
                "email": email,
                "timestamp": token_time,
                "valid": True
            }

        except Exception:
            return {"valid": False}
```

## 📊 Analytics & Monitoring

### Magic Link Usage Analytics

```python
from sqlalchemy import func
from app.models import MagicLink, ActivityLog

class MagicLinkAnalytics:
    def __init__(self, db: Session):
        self.db = db

    def get_usage_stats(self, days: int = 30) -> dict:
        """Get magic link usage statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Magic link requests
        requests = self.db.query(func.count(ActivityLog.id)).filter(
            ActivityLog.action == "magic_link_requested",
            ActivityLog.created_at >= cutoff_date
        ).scalar()

        # Successful verifications
        verifications = self.db.query(func.count(ActivityLog.id)).filter(
            ActivityLog.action == "magic_link_verified",
            ActivityLog.created_at >= cutoff_date
        ).scalar()

        # Conversion rate
        conversion_rate = (verifications / requests * 100) if requests > 0 else 0

        # Popular redirect URLs
        popular_redirects = self.db.query(
            ActivityLog.details['redirect_url'].astext,
            func.count(ActivityLog.id).label('count')
        ).filter(
            ActivityLog.action == "magic_link_requested",
            ActivityLog.created_at >= cutoff_date,
            ActivityLog.details.has_key('redirect_url')
        ).group_by(
            ActivityLog.details['redirect_url'].astext
        ).order_by(func.count(ActivityLog.id).desc()).limit(5).all()

        return {
            "requests": requests,
            "verifications": verifications,
            "conversion_rate": round(conversion_rate, 2),
            "popular_redirects": [
                {"url": url, "count": count}
                for url, count in popular_redirects
            ]
        }

    def get_failure_analysis(self, days: int = 7) -> dict:
        """Analyze magic link failures"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Expired token attempts
        expired_attempts = self.db.query(func.count(ActivityLog.id)).filter(
            ActivityLog.action == "magic_link_expired",
            ActivityLog.created_at >= cutoff_date
        ).scalar()

        # Invalid token attempts
        invalid_attempts = self.db.query(func.count(ActivityLog.id)).filter(
            ActivityLog.action == "magic_link_invalid",
            ActivityLog.created_at >= cutoff_date
        ).scalar()

        # Rate limit hits
        rate_limited = self.db.query(func.count(ActivityLog.id)).filter(
            ActivityLog.action == "magic_link_rate_limited",
            ActivityLog.created_at >= cutoff_date
        ).scalar()

        return {
            "expired_attempts": expired_attempts,
            "invalid_attempts": invalid_attempts,
            "rate_limited": rate_limited,
            "total_failures": expired_attempts + invalid_attempts + rate_limited
        }
```

## 🔍 Troubleshooting

### Common Issues and Solutions

**Issue: Magic link emails not being delivered**
```python
def debug_email_delivery():
    """Debug email delivery issues"""

    # Check email service configuration
    print(f"SMTP Host: {settings.SMTP_HOST}")
    print(f"SMTP Port: {settings.SMTP_PORT}")
    print(f"Email Enabled: {settings.EMAIL_ENABLED}")

    # Test email connectivity
    try:
        email_service = EmailService()
        await email_service.test_connection()
        print("✅ Email service connected")
    except Exception as e:
        print(f"❌ Email service error: {e}")

    # Check for email in spam/junk folder
    print("📧 Check recipient's spam/junk folder")
```

**Issue: "Invalid or expired magic link"**
```python
def debug_magic_link_token(token: str):
    """Debug magic link token issues"""

    try:
        # Check token format
        import base64
        decoded = base64.b64decode(token.encode())
        print(f"Token decodes successfully: {len(decoded)} bytes")

        # Verify with magic link service
        token_service = SecureMagicLinkToken()
        result = token_service.verify_token(token)

        if result["valid"]:
            print("✅ Token is valid")
            print(f"User: {result['email']}")
            print(f"Generated: {result['timestamp']}")
        else:
            print("❌ Token is invalid or expired")

    except Exception as e:
        print(f"Token parsing error: {e}")
```

**Issue: Rate limiting blocking legitimate users**
```python
async def reset_rate_limit(email: str):
    """Reset rate limit for specific email (admin function)"""

    keys = [
        f"magic_link:email:{email}:hour",
        f"magic_link:email:{email}:day"
    ]

    for key in keys:
        await redis_client.delete(key)

    print(f"✅ Rate limit reset for {email}")
```

## 📚 API Reference

### Complete Endpoint Documentation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/magic-link` | POST | Send magic link |
| `/api/v1/auth/magic-link/verify` | POST | Verify magic link token |

### Request/Response Schemas

**Send Magic Link Request:**
```json
{
  "email": "user@example.com",
  "redirect_url": "https://myapp.com/callback" // optional
}
```

**Magic Link Verification Request:**
```json
{
  "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

For complete API documentation, see:
- [Authentication API Reference](../api/authentication.md)
- [Error Handling Guide](../api/error-handling.md)

## 🎯 Advanced Features

### Integration with Multi-Factor Authentication

```javascript
// Combined MFA + Magic Link flow
const handleSecureLogin = async (email) => {
  // Step 1: Send magic link
  await magicLinkAuth.sendMagicLink(email);

  // Step 2: User clicks magic link, gets temporary session
  const tempSession = await magicLinkAuth.verifyMagicLink(token);

  // Step 3: If MFA enabled, require additional verification
  if (tempSession.user.mfa_enabled) {
    const mfaCode = await promptForMFACode();
    await mfaService.validateCode(mfaCode);
  }

  // Step 4: Complete authentication
  return tempSession;
};
```

### Progressive Enhancement

```javascript
class EnhancedMagicLinkAuth extends MagicLinkAuth {
  async sendMagicLinkWithFallback(email) {
    try {
      // Try magic link first
      return await this.sendMagicLink(email);
    } catch (error) {
      if (error.message.includes('Magic links are disabled')) {
        // Fallback to password reset flow
        return await this.sendPasswordReset(email);
      }
      throw error;
    }
  }

  async smartAuthFlow(email) {
    // Check user preferences
    const userPrefs = await this.getUserPreferences(email);

    if (userPrefs.preferred_auth === 'magic_link') {
      return await this.sendMagicLink(email);
    } else {
      // Default to password flow
      return { method: 'password', message: 'Please enter your password' };
    }
  }
}
```

---

**🔐 [Security Documentation](../security/README.md)** • **🔗 [API Reference](../api/README.md)** • **✉️ [Email Templates](../deployment/email-templates.md)**