# Multi-Factor Authentication (MFA/2FA) Implementation Guide

> **Complete guide to implementing TOTP-based multi-factor authentication with backup codes**

## Overview

Plinto API provides enterprise-grade MFA/2FA using Time-based One-Time Passwords (TOTP) compatible with Google Authenticator, Authy, and other standard authenticator apps. This guide covers the complete implementation process.

## 🔐 MFA Features

### Core Capabilities
- **TOTP Authentication**: RFC 6238 compliant time-based codes
- **QR Code Generation**: Automatic setup with authenticator apps
- **Backup Codes**: 10 recovery codes for account access
- **Recovery Options**: Email-based account recovery
- **Activity Logging**: Complete audit trail of MFA events
- **Rate Limiting**: Protection against brute force attacks

### Security Features
- **6-digit codes** with 30-second validity window
- **Backup code tracking** with usage monitoring
- **Password verification** required for sensitive operations
- **Automatic lockout** after failed attempts
- **Secure provisioning** with cryptographically random secrets

## 🚀 Quick Start

### 1. Enable MFA for User

```bash
# Step 1: Initiate MFA setup
curl -X POST "https://api.plinto.dev/api/v1/mfa/enable" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "user_current_password"
  }'
```

**Response includes QR code and backup codes:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "backup_codes": [
    "ABCD-1234",
    "EFGH-5678",
    "IJKL-9012"
  ],
  "provisioning_uri": "otpauth://totp/user@example.com?secret=JBSWY..."
}
```

### 2. Verify MFA Setup

```bash
# Step 2: Verify with code from authenticator app
curl -X POST "https://api.plinto.dev/api/v1/mfa/verify" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "123456"
  }'
```

### 3. Check MFA Status

```bash
curl -H "Authorization: Bearer <access_token>" \
     "https://api.plinto.dev/api/v1/mfa/status"
```

**Response:**
```json
{
  "enabled": true,
  "verified": true,
  "backup_codes_remaining": 8,
  "last_used_at": "2025-01-16T10:30:00Z"
}
```

## 📱 Client Implementation

### Frontend Integration Example

```javascript
class MFAManager {
  constructor(apiClient) {
    this.api = apiClient;
  }

  // Enable MFA
  async enableMFA(password) {
    try {
      const response = await this.api.post('/api/v1/mfa/enable', {
        password
      });

      return {
        qrCode: response.data.qr_code,
        backupCodes: response.data.backup_codes,
        secret: response.data.secret
      };
    } catch (error) {
      throw new Error(`MFA enable failed: ${error.response.data.detail}`);
    }
  }

  // Verify MFA setup
  async verifyMFA(code) {
    try {
      await this.api.post('/api/v1/mfa/verify', {
        code
      });
      return { success: true };
    } catch (error) {
      throw new Error(`MFA verification failed: ${error.response.data.detail}`);
    }
  }

  // Get MFA status
  async getStatus() {
    const response = await this.api.get('/api/v1/mfa/status');
    return response.data;
  }

  // Validate MFA code
  async validateCode(code) {
    try {
      const response = await this.api.post('/api/v1/mfa/validate-code', {
        code
      });
      return response.data.valid;
    } catch (error) {
      return false;
    }
  }

  // Disable MFA
  async disableMFA(password, code = null) {
    await this.api.post('/api/v1/mfa/disable', {
      password,
      code
    });
  }

  // Regenerate backup codes
  async regenerateBackupCodes(password) {
    const response = await this.api.post('/api/v1/mfa/regenerate-backup-codes', {
      password
    });
    return response.data.backup_codes;
  }
}
```

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';
import QRCode from 'qrcode.react';

const MFASetup = ({ user, onComplete }) => {
  const [step, setStep] = useState('password');
  const [password, setPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [mfaData, setMfaData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleEnableMFA = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const mfaManager = new MFAManager(apiClient);
      const data = await mfaManager.enableMFA(password);
      setMfaData(data);
      setStep('verify');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyMFA = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const mfaManager = new MFAManager(apiClient);
      await mfaManager.verifyMFA(verificationCode);
      setStep('complete');
      onComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mfa-setup">
      {step === 'password' && (
        <form onSubmit={handleEnableMFA}>
          <h2>Enable Two-Factor Authentication</h2>
          <p>Enter your password to set up MFA:</p>

          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Current password"
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? 'Setting up...' : 'Enable MFA'}
          </button>

          {error && <div className="error">{error}</div>}
        </form>
      )}

      {step === 'verify' && mfaData && (
        <form onSubmit={handleVerifyMFA}>
          <h2>Scan QR Code</h2>
          <p>Scan this QR code with your authenticator app:</p>

          <QRCode value={mfaData.qrCode} size={200} />

          <h3>Backup Codes</h3>
          <p>Save these backup codes in a secure location:</p>
          <div className="backup-codes">
            {mfaData.backupCodes.map((code, index) => (
              <code key={index}>{code}</code>
            ))}
          </div>

          <h3>Verify Setup</h3>
          <p>Enter the 6-digit code from your authenticator app:</p>

          <input
            type="text"
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value)}
            placeholder="123456"
            maxLength="6"
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? 'Verifying...' : 'Verify & Enable'}
          </button>

          {error && <div className="error">{error}</div>}
        </form>
      )}

      {step === 'complete' && (
        <div>
          <h2>✅ MFA Enabled Successfully</h2>
          <p>Two-factor authentication is now active for your account.</p>
        </div>
      )}
    </div>
  );
};
```

## 🔧 Backend Integration

### Authentication Middleware Integration

```python
from fastapi import Depends, HTTPException
from app.dependencies import get_current_user
from app.models import User

async def require_mfa_if_enabled(
    current_user: User = Depends(get_current_user),
    mfa_verified: bool = False
):
    """Middleware to require MFA verification if enabled"""
    if current_user.mfa_enabled and not mfa_verified:
        raise HTTPException(
            status_code=403,
            detail="MFA verification required",
            headers={"X-MFA-Required": "true"}
        )
    return current_user

# Usage in protected endpoints
@router.get("/sensitive-data")
async def get_sensitive_data(
    current_user: User = Depends(require_mfa_if_enabled)
):
    """Endpoint requiring MFA if enabled"""
    return {"data": "sensitive information"}
```

### MFA Service Integration

```python
from app.routers.v1.mfa import validate_mfa_code

class AuthenticationService:
    async def authenticate_with_mfa(
        self,
        email: str,
        password: str,
        mfa_code: str = None
    ):
        """Complete authentication flow with MFA support"""

        # Standard password authentication
        user = await self.authenticate_user(email, password)
        if not user:
            raise HTTPException(401, "Invalid credentials")

        # Check if MFA is required
        if user.mfa_enabled:
            if not mfa_code:
                raise HTTPException(
                    401,
                    "MFA code required",
                    headers={"X-MFA-Required": "true"}
                )

            # Validate MFA code
            mfa_valid = await validate_mfa_code(mfa_code, user)
            if not mfa_valid:
                raise HTTPException(401, "Invalid MFA code")

        # Generate tokens
        return await self.create_user_session(user)
```

## 🛡️ Security Best Practices

### Rate Limiting Configuration

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/mfa/verify")
@limiter.limit("10/minute")  # 10 attempts per minute
@limiter.limit("50/hour")    # 50 attempts per hour
async def verify_mfa(request, ...):
    """Rate-limited MFA verification"""
    pass
```

### Secure Storage

```python
from cryptography.fernet import Fernet
import os

class MFASecretManager:
    def __init__(self):
        # Use environment variable for encryption key
        self.cipher = Fernet(os.environ['MFA_ENCRYPTION_KEY'])

    def encrypt_secret(self, secret: str) -> str:
        """Encrypt MFA secret before storage"""
        return self.cipher.encrypt(secret.encode()).decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt MFA secret for verification"""
        return self.cipher.decrypt(encrypted_secret.encode()).decode()
```

### Backup Code Security

```python
import hashlib
import secrets

def generate_secure_backup_codes(count: int = 10) -> list:
    """Generate cryptographically secure backup codes"""
    codes = []
    for _ in range(count):
        # Generate 16 bytes of randomness
        raw_code = secrets.token_bytes(16)
        # Create readable format
        code = raw_code.hex()[:8].upper()
        formatted = f"{code[:4]}-{code[4:]}"
        codes.append(formatted)
    return codes

def hash_backup_code(code: str) -> str:
    """Hash backup codes for secure storage"""
    return hashlib.sha256(code.encode()).hexdigest()
```

## 📊 Analytics & Monitoring

### MFA Usage Metrics

```python
from app.models import ActivityLog
from sqlalchemy import func

class MFAAnalytics:
    def __init__(self, db: Session):
        self.db = db

    def get_mfa_adoption_rate(self) -> float:
        """Calculate MFA adoption rate"""
        total_users = self.db.query(User).filter(
            User.status == UserStatus.ACTIVE
        ).count()

        mfa_users = self.db.query(User).filter(
            User.status == UserStatus.ACTIVE,
            User.mfa_enabled == True
        ).count()

        return (mfa_users / total_users) * 100 if total_users > 0 else 0

    def get_mfa_usage_stats(self, days: int = 30):
        """Get MFA usage statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stats = self.db.query(
            ActivityLog.action,
            func.count(ActivityLog.id).label('count')
        ).filter(
            ActivityLog.created_at >= cutoff_date,
            ActivityLog.action.in_([
                'mfa_enabled', 'mfa_disabled', 'mfa_verify',
                'mfa_backup_code_used', 'mfa_recovery_initiated'
            ])
        ).group_by(ActivityLog.action).all()

        return {stat.action: stat.count for stat in stats}
```

## 🔍 Troubleshooting

### Common Issues

**Issue: "Invalid verification code"**
```python
# Check time synchronization
import time
import pyotp

def debug_totp_timing(secret: str, user_code: str):
    """Debug TOTP timing issues"""
    totp = pyotp.TOTP(secret)
    current_time = int(time.time())

    # Check current and adjacent time windows
    for offset in [-1, 0, 1]:
        test_time = current_time + (offset * 30)
        expected_code = totp.at(test_time)
        print(f"Time offset {offset*30}s: expected {expected_code}")

        if expected_code == user_code:
            print(f"✅ Code valid with {offset*30}s offset")
            return True

    return False
```

**Issue: QR code not scanning**
```python
def validate_qr_code_uri(secret: str, email: str, issuer: str):
    """Validate QR code URI format"""
    expected_uri = f"otpauth://totp/{email}?secret={secret}&issuer={issuer}"
    print(f"Expected URI: {expected_uri}")

    # Test with different URI formats
    test_formats = [
        f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}",
        f"otpauth://totp/{email}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
    ]

    for uri in test_formats:
        print(f"Test URI: {uri}")
```

### Error Handling

```python
class MFAError(Exception):
    """Base MFA exception"""
    pass

class MFANotEnabledError(MFAError):
    """MFA not enabled for user"""
    pass

class InvalidMFACodeError(MFAError):
    """Invalid MFA code provided"""
    pass

class MFAAlreadyEnabledError(MFAError):
    """MFA already enabled for user"""
    pass

def handle_mfa_errors(func):
    """Decorator for consistent MFA error handling"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MFANotEnabledError:
            raise HTTPException(400, "MFA is not enabled")
        except InvalidMFACodeError:
            raise HTTPException(400, "Invalid verification code")
        except MFAAlreadyEnabledError:
            raise HTTPException(400, "MFA is already enabled")
        except Exception as e:
            logger.error(f"MFA operation failed: {e}")
            raise HTTPException(500, "MFA operation failed")
    return wrapper
```

## 📚 API Reference

### Endpoints Summary

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/mfa/status` | GET | Get MFA status |
| `/api/v1/mfa/enable` | POST | Enable MFA |
| `/api/v1/mfa/verify` | POST | Verify MFA setup |
| `/api/v1/mfa/disable` | POST | Disable MFA |
| `/api/v1/mfa/validate-code` | POST | Validate MFA code |
| `/api/v1/mfa/regenerate-backup-codes` | POST | Regenerate backup codes |
| `/api/v1/mfa/recovery-options` | GET | Get recovery options |
| `/api/v1/mfa/initiate-recovery` | POST | Initiate account recovery |
| `/api/v1/mfa/supported-methods` | GET | Get supported MFA methods |

### Complete API Documentation

For detailed API documentation with request/response schemas, see:
- [Complete API Reference](../api/README.md#multi-factor-authentication)
- [Authentication Guide](../api/authentication.md#mfa-integration)

## 🎯 Next Steps

1. **Implement SMS MFA**: Add SMS-based verification for additional security
2. **Hardware Security Keys**: Integrate WebAuthn for hardware-based MFA
3. **Risk-Based Authentication**: Implement adaptive MFA based on login patterns
4. **Mobile App Integration**: Create dedicated mobile authenticator app
5. **Enterprise SSO Integration**: Connect MFA with SAML/SCIM flows

---

**🔐 [Security Documentation](../security/README.md)** • **🔗 [API Reference](../api/README.md)** • **📱 [Client SDKs](../api/sdks.md)**