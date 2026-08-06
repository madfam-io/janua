# SSO Integration Guide

**Version**: 1.0.0-beta  
**Last Updated**: November 16, 2025  
**Applies to**: Enterprise Plan

> [!NOTE]
> **Claim status: Roadmap/Beta.** Per the
> [GA claim matrix](../enterprise/GA_CLAIM_MATRIX.md), enterprise SAML SSO is
> not commercially GA — it may be offered to selected customers only after a
> customer-specific IdP proof and support runbook exist.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Supported Providers](#supported-providers)
4. [SAML Integration](#saml-integration)
5. [OAuth 2.0 / OIDC Integration](#oauth-20--oidc-integration)
6. [Provider-Specific Guides](#provider-specific-guides)
7. [Testing SSO](#testing-sso)
8. [Troubleshooting](#troubleshooting)
9. [Security Best Practices](#security-best-practices)

---

## Overview

Single Sign-On (SSO) allows your organization's users to authenticate using your existing identity provider, eliminating the need for separate Janua credentials.

### Benefits

✅ **Centralized Authentication**: Manage user access from one place  
✅ **Enhanced Security**: Leverage your existing security policies  
✅ **Improved UX**: One-click login for users  
✅ **Automatic Provisioning**: Works with SCIM for user sync  
✅ **Audit Trail**: Complete login history and compliance  

### How It Works

```
┌─────────┐           ┌─────────────┐           ┌────────┐
│  User   │──(1)─────▶│   Janua    │──(2)─────▶│  IdP   │
│         │           │             │           │        │
│         │◀──(6)─────│             │◀──(3)─────│        │
└─────────┘           └─────────────┘           └────────┘
                             │                       │
                             └──────(4)──────────────┘
                                    (5)

1. User visits Janua login page
2. Janua redirects to Identity Provider (IdP)
3. User authenticates with IdP
4. IdP sends SAML assertion/OAuth token to Janua
5. Janua validates and creates session
6. User is logged in to Janua
```

---

## Prerequisites

### Requirements

Before setting up SSO, ensure you have:

- ✅ **Enterprise Plan**: SSO is available on Enterprise plan only
- ✅ **Organization Admin Access**: You must be an organization administrator
- ✅ **IdP Admin Access**: Access to configure your identity provider
- ✅ **Domain Verification**: Verified domain ownership in Janua
- ✅ **SSL Certificate**: HTTPS endpoint for production use

### Information Needed

From your Identity Provider:
- Entity ID / Issuer URL
- Single Sign-On URL
- X.509 Certificate (for SAML)
- Client ID / Client Secret (for OAuth)

From Janua (provided during setup):
- Service Provider Entity ID
- Assertion Consumer Service (ACS) URL
- Sign-on URL
- Logout URL

---

## Supported Providers

### SAML 2.0

- ✅ Okta
- ✅ Azure AD / Microsoft Entra ID
- ✅ Google Workspace
- ✅ OneLogin
- ✅ Auth0
- ✅ JumpCloud
- ✅ Generic SAML 2.0

### OAuth 2.0 / OIDC

- ✅ Google Workspace (OAuth)
- ✅ Microsoft Azure AD (OAuth)
- ✅ Okta (OIDC)
- ✅ Auth0 (OIDC)
- ✅ Generic OIDC

---

## SAML Integration

### Step 1: Configure Janua as Service Provider

1. **Navigate to SSO Settings**
   - Go to Organization Settings → Security → Single Sign-On
   - Click "Configure SSO"

2. **Select Provider**
   - Choose your identity provider from the list
   - Or select "Generic SAML 2.0" for other providers

3. **Copy Janua Metadata**
   
   You'll need these values for your IdP configuration:
   
   ```
   Entity ID (Audience URI):
   https://api.janua.dev/sso/saml/{organization_id}
   
   Assertion Consumer Service (ACS) URL:
   https://api.janua.dev/sso/saml/{organization_id}/acs
   
   Single Logout Service URL:
   https://api.janua.dev/sso/saml/{organization_id}/sls
   ```

### Step 2: Configure Identity Provider

#### Required SAML Attributes

Janua requires the following SAML attributes:

| Attribute | Required | Format | Example |
|-----------|----------|--------|---------|
| `email` | ✅ Yes | Email address | user@example.com |
| `firstName` | ✅ Yes | String | John |
| `lastName` | ✅ Yes | String | Doe |
| `groups` | ⚠️ Optional | Array of strings | ["Engineering", "Admin"] |

#### Example SAML Assertion

```xml
<saml:AttributeStatement>
  <saml:Attribute Name="email">
    <saml:AttributeValue>user@example.com</saml:AttributeValue>
  </saml:Attribute>
  <saml:Attribute Name="firstName">
    <saml:AttributeValue>John</saml:AttributeValue>
  </saml:Attribute>
  <saml:Attribute Name="lastName">
    <saml:AttributeValue>Doe</saml:AttributeValue>
  </saml:Attribute>
  <saml:Attribute Name="groups">
    <saml:AttributeValue>Engineering</saml:AttributeValue>
    <saml:AttributeValue>Admin</saml:AttributeValue>
  </saml:Attribute>
</saml:AttributeStatement>
```

### Step 3: Add IdP Metadata to Janua

1. **Obtain IdP Metadata**
   - Download metadata XML from your IdP
   - Or manually enter Entity ID, SSO URL, and Certificate

2. **Upload to Janua**
   - Paste metadata XML in configuration form
   - Or fill in manual fields:
     - **Entity ID**: Your IdP's entity identifier
     - **SSO URL**: Single Sign-On endpoint
     - **Certificate**: X.509 signing certificate

3. **Configure Domains**
   - Add email domains that should use SSO
   - Example: `example.com`, `company.com`
   - Users with these domains will be redirected to SSO

### Step 4: Test and Enable

1. **Test SSO Flow**
   - Click "Test SSO Connection"
   - Complete authentication flow
   - Verify user attributes are mapped correctly

2. **Enable SSO**
   - Toggle "Enable SSO" switch
   - Choose enforcement mode:
     - **Optional**: Users can choose SSO or password
     - **Required**: All users must use SSO
     - **Domain-based**: Auto-redirect based on email domain

---

## OAuth 2.0 / OIDC Integration

### Step 1: Register Janua Application

In your OAuth provider:

1. **Create OAuth Application**
   - Application Name: `Janua SSO`
   - Application Type: `Web Application`
   
2. **Configure Redirect URIs**
   ```
   https://api.janua.dev/sso/oauth/{organization_id}/callback
   https://app.janua.dev/auth/callback
   ```

3. **Configure Scopes**
   Required scopes:
   - `openid`
   - `email`
   - `profile`
   
   Optional scopes:
   - `groups` (for role mapping)

4. **Obtain Credentials**
   - Copy **Client ID**
   - Copy **Client Secret**
   - Note **Authorization URL**
   - Note **Token URL**
   - Note **UserInfo URL** (if using OIDC)

### Step 2: Configure OAuth in Janua

1. **Navigate to SSO Settings**
   - Organization Settings → Security → Single Sign-On
   - Select "OAuth 2.0 / OIDC"

2. **Enter OAuth Details**
   ```
   Client ID: your_client_id
   Client Secret: your_client_secret
   Authorization URL: https://idp.example.com/oauth/authorize
   Token URL: https://idp.example.com/oauth/token
   UserInfo URL: https://idp.example.com/oauth/userinfo
   ```

3. **Configure Attribute Mapping**
   Map IdP attributes to Janua fields:
   
   | Janua Field | IdP Attribute |
   |--------------|---------------|
   | Email | `email` |
   | First Name | `given_name` |
   | Last Name | `family_name` |
   | Groups | `groups` or `roles` |

### Step 3: Test and Enable

Same as SAML Step 4 above.

---

## Provider-Specific Guides

### Okta

#### SAML Configuration

1. **Create SAML Application in Okta**
   - Admin Console → Applications → Create App Integration
   - Sign-in method: SAML 2.0
   - App name: Janua

2. **Configure SAML Settings**
   ```
   Single sign-on URL: https://api.janua.dev/sso/saml/{org_id}/acs
   Audience URI: https://api.janua.dev/sso/saml/{org_id}
   Name ID format: EmailAddress
   Application username: Email
   ```

3. **Configure Attribute Statements**
   ```
   email → user.email
   firstName → user.firstName
   lastName → user.lastName
   groups → appuser.groups (if using)
   ```

4. **Assign Users**
   - Assign individuals or groups
   - Users will see Janua in their Okta dashboard

5. **Download Metadata**
   - Sign On tab → View SAML setup instructions
   - Copy "Identity Provider metadata" link
   - Paste into Janua SSO configuration

#### OIDC Configuration

1. **Create OIDC Application**
   - Applications → Create App Integration
   - Sign-in method: OIDC - Web Application

2. **Configure Application**
   ```
   Sign-in redirect URIs:
   - https://api.janua.dev/sso/oauth/{org_id}/callback
   - https://app.janua.dev/auth/callback
   
   Sign-out redirect URIs:
   - https://app.janua.dev/logout
   
   Assignments: Limit to selected groups
   ```

3. **Copy Credentials**
   - Client ID
   - Client Secret
   - Okta domain: `https://{your-domain}.okta.com`

4. **Configure in Janua**
   ```
   Authorization URL: https://{domain}.okta.com/oauth2/v1/authorize
   Token URL: https://{domain}.okta.com/oauth2/v1/token
   UserInfo URL: https://{domain}.okta.com/oauth2/v1/userinfo
   ```

---

### Azure AD / Microsoft Entra ID

#### SAML Configuration

1. **Create Enterprise Application**
   - Azure Portal → Entra ID → Enterprise applications
   - New application → Create your own application
   - Name: Janua
   - Integrate any other application (non-gallery)

2. **Configure Single Sign-On**
   - Single sign-on → SAML
   - Basic SAML Configuration:
     ```
     Identifier (Entity ID): https://api.janua.dev/sso/saml/{org_id}
     Reply URL (ACS): https://api.janua.dev/sso/saml/{org_id}/acs
     Sign on URL: https://app.janua.dev/login
     ```

3. **Configure Attributes & Claims**
   ```
   Required claims:
   - email → user.mail
   - firstName → user.givenname
   - lastName → user.surname
   
   Optional claims:
   - groups → user.groups (requires group claim configuration)
   ```

4. **Download Certificate**
   - SAML Signing Certificate section
   - Download "Certificate (Base64)"
   - Copy "Login URL" and "Azure AD Identifier"

5. **Assign Users**
   - Users and groups → Add user/group
   - Select users or groups to grant access

#### OIDC Configuration

1. **Register Application**
   - App registrations → New registration
   - Name: Janua
   - Supported account types: Single tenant
   - Redirect URI:
     ```
     Web: https://api.janua.dev/sso/oauth/{org_id}/callback
     ```

2. **Configure API Permissions**
   - API permissions → Add permission
   - Microsoft Graph → Delegated permissions:
     - `openid`
     - `email`
     - `profile`
     - `User.Read`
     - `GroupMember.Read.All` (optional, for groups)

3. **Create Client Secret**
   - Certificates & secrets → New client secret
   - Description: Janua SSO
   - Copy secret value (only shown once!)

4. **Copy Application Details**
   ```
   Application (client) ID: {client_id}
   Directory (tenant) ID: {tenant_id}
   Client secret: {secret_value}
   ```

5. **Configure in Janua**
   ```
   Client ID: {client_id}
   Client Secret: {secret_value}
   Authorization URL: https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize
   Token URL: https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token
   UserInfo URL: https://graph.microsoft.com/oidc/userinfo
   ```

---

### Google Workspace

#### SAML Configuration

1. **Add Custom SAML Application**
   - Admin Console → Apps → Web and mobile apps
   - Add app → Add custom SAML app
   - App name: Janua

2. **Download Google IdP Metadata**
   - Copy SSO URL
   - Copy Entity ID
   - Download Certificate

3. **Configure Service Provider**
   ```
   ACS URL: https://api.janua.dev/sso/saml/{org_id}/acs
   Entity ID: https://api.janua.dev/sso/saml/{org_id}
   Start URL: https://app.janua.dev/login
   Name ID format: EMAIL
   Name ID: Basic Information > Primary email
   ```

4. **Configure Attribute Mapping**
   ```
   Primary email → email
   First name → firstName
   Last name → lastName
   ```

5. **Enable for Users**
   - User access → ON for everyone
   - Or select organizational units

#### OAuth Configuration

1. **Create OAuth Client**
   - Google Cloud Console → APIs & Services → Credentials
   - Create Credentials → OAuth client ID
   - Application type: Web application
   - Name: Janua

2. **Configure Redirect URIs**
   ```
   Authorized redirect URIs:
   - https://api.janua.dev/sso/oauth/{org_id}/callback
   - https://app.janua.dev/auth/callback
   ```

3. **Configure OAuth Consent Screen**
   - User Type: Internal (for Workspace users)
   - Scopes:
     - `openid`
     - `email`
     - `profile`

4. **Copy Credentials**
   - Client ID
   - Client Secret

5. **Configure in Janua**
   ```
   Client ID: {client_id}.apps.googleusercontent.com
   Client Secret: {client_secret}
   Authorization URL: https://accounts.google.com/o/oauth2/v2/auth
   Token URL: https://oauth2.googleapis.com/token
   UserInfo URL: https://openidconnect.googleapis.com/v1/userinfo
   ```

---

### OneLogin

#### SAML Configuration

1. **Add SAML Application**
   - Applications → Add App
   - Search: "SAML Custom Connector (Advanced)"
   - Display Name: Janua

2. **Configure SSO**
   - Configuration tab:
     ```
     Audience: https://api.janua.dev/sso/saml/{org_id}
     Recipient: https://api.janua.dev/sso/saml/{org_id}/acs
     ACS URL: https://api.janua.dev/sso/saml/{org_id}/acs
     ACS URL Validator: ^https://api\.janua\.dev/.*$
     ```

3. **Configure Parameters**
   ```
   email → Email
   firstName → First Name
   lastName → Last Name
   groups → Member Of (if using groups)
   ```

4. **Download Metadata**
   - SSO tab → Issuer URL
   - Copy "SAML 2.0 Endpoint (HTTP)"
   - Download X.509 Certificate

5. **Assign Users**
   - Access tab → Add users or roles

---

## Testing SSO

### Test Checklist

Before enabling SSO for all users:

- [ ] **Metadata Exchange Complete**
  - IdP metadata uploaded to Janua
  - SP metadata configured in IdP

- [ ] **Attribute Mapping Verified**
  - Email, first name, last name correctly mapped
  - Groups mapped (if using RBAC integration)

- [ ] **Test User Authentication**
  - Create test user in IdP
  - Initiate SSO from Janua
  - Verify successful login
  - Check user profile data in Janua

- [ ] **Test Logout**
  - Logout from Janua
  - Verify session terminated
  - Test Single Logout (SLO) if configured

- [ ] **Test Edge Cases**
  - User doesn't exist in Janua (JIT provisioning)
  - User exists with different email
  - Invalid SAML assertion
  - Expired certificate

### Test SSO Flow

1. **Initiate SSO Login**
   ```
   https://app.janua.dev/login?domain=example.com
   ```
   
   Or use direct SSO URL:
   ```
   https://app.janua.dev/sso/{organization_id}
   ```

2. **Verify Redirect**
   - User redirected to IdP login page
   - Correct organization context maintained

3. **Complete Authentication**
   - Login with test credentials
   - Verify redirect back to Janua

4. **Check User Session**
   - User logged in automatically
   - Correct profile information displayed
   - Appropriate role/permissions assigned

### Debug Mode

Enable debug mode for detailed SSO logs:

1. **Enable Debug Logging**
   - Organization Settings → SSO → Advanced
   - Toggle "Enable Debug Logging"

2. **View Logs**
   - Navigate to SSO Logs
   - Filter by test user email
   - Review SAML assertions or OAuth responses

3. **Common Debug Info**
   ```json
   {
     "timestamp": "2025-11-16T15:30:00Z",
     "event": "saml_assertion_received",
     "user_email": "test@example.com",
     "attributes": {
       "email": "test@example.com",
       "firstName": "Test",
       "lastName": "User"
     },
     "status": "success"
   }
   ```

---

## Troubleshooting

### Common Issues

#### 1. SAML Assertion Invalid

**Error**: "Invalid SAML assertion signature"

**Causes**:
- Certificate mismatch
- Clock skew between servers
- Incorrect entity ID

**Solutions**:
- Verify certificate in Janua matches IdP
- Check server time synchronization (NTP)
- Confirm entity ID exactly matches
- Check SAML assertion in debug logs

#### 2. Attribute Mapping Issues

**Error**: "Required attribute 'email' not found"

**Causes**:
- Attribute name mismatch
- Attribute not included in assertion
- Case sensitivity issues

**Solutions**:
- Review SAML assertion in debug logs
- Verify attribute names in IdP configuration
- Check Janua attribute mapping settings
- Use attribute mapping overrides if needed

#### 3. User Not Provisioned

**Error**: "User not found in organization"

**Causes**:
- Just-in-Time (JIT) provisioning disabled
- User email doesn't match verified domains
- Organization not found

**Solutions**:
- Enable JIT provisioning in SSO settings
- Add user's email domain to allowed domains
- Verify organization ID in SSO URL

#### 4. OAuth Token Expired

**Error**: "Invalid or expired OAuth token"

**Causes**:
- Token lifetime too short
- Clock skew
- Token not refreshed

**Solutions**:
- Check token expiry settings in IdP
- Verify server time synchronization
- Enable automatic token refresh

#### 5. Redirect Loop

**Error**: Continuous redirects between Janua and IdP

**Causes**:
- Incorrect redirect URLs
- Session cookie issues
- Browser privacy settings

**Solutions**:
- Verify ACS URL matches exactly
- Check browser allows third-party cookies
- Clear browser cache and cookies
- Test in incognito/private mode

### Support Resources

- **Documentation**: https://docs.janua.dev/sso
- **Community Forum**: https://community.janua.dev
- **Email Support**: sso-support@janua.dev
- **Enterprise Support**: Available 24/7 for Enterprise customers

---

## Security Best Practices

### 1. Certificate Management

✅ **Do:**
- Use strong X.509 certificates (2048-bit RSA minimum)
- Rotate certificates before expiration
- Store certificates securely
- Use separate certificates for different environments

❌ **Don't:**
- Use self-signed certificates in production
- Share certificates between applications
- Commit certificates to version control

### 2. Attribute Assertions

✅ **Do:**
- Validate all SAML assertions
- Use signed and encrypted assertions
- Limit assertion lifetime (5-10 minutes)
- Require audience restriction

❌ **Don't:**
- Accept unsigned assertions
- Trust attributes without validation
- Use bearer assertions without encryption

### 3. Access Control

✅ **Do:**
- Use group-based role mapping
- Implement least privilege principle
- Audit SSO login events
- Require MFA at IdP level

❌ **Don't:**
- Grant admin access by default
- Skip authorization checks
- Ignore failed login attempts

### 4. Network Security

✅ **Do:**
- Use HTTPS for all endpoints
- Implement IP allowlisting (if applicable)
- Use VPN for admin access
- Enable DDoS protection

❌ **Don't:**
- Expose metadata publicly
- Use HTTP for sensitive operations
- Allow plaintext SAML assertions

### 5. Monitoring & Auditing

✅ **Do:**
- Monitor all SSO login attempts
- Alert on failed authentications
- Log all configuration changes
- Review audit logs regularly

❌ **Don't:**
- Disable logging for performance
- Ignore security alerts
- Store logs indefinitely without retention policy

---

## Advanced Configuration

### Just-in-Time (JIT) Provisioning

Automatically create user accounts on first SSO login:

```javascript
// Enable JIT provisioning
{
  "jit_provisioning": true,
  "default_role": "user",
  "attribute_mapping": {
    "email": "email",
    "firstName": "given_name",
    "lastName": "family_name"
  },
  "allowed_domains": ["example.com"]
}
```

### Role Mapping

Map IdP groups to Janua roles:

```javascript
{
  "role_mapping": {
    "Engineering": "developer",
    "Admin": "admin",
    "HR": "user"
  }
}
```

### Single Logout (SLO)

Enable logout from Janua to terminate IdP session:

```xml
<SingleLogoutService
  Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
  Location="https://api.janua.dev/sso/saml/{org_id}/sls"
/>
```

---

## Migration Guide

### From Password to SSO

1. **Communicate with Users**
   - Announce SSO rollout timeline
   - Provide training materials
   - Offer support channels

2. **Pilot Testing**
   - Enable SSO for small group
   - Collect feedback
   - Fix issues before full rollout

3. **Gradual Rollout**
   - Keep password auth enabled initially
   - Monitor adoption rate
   - Address support requests

4. **Enforce SSO**
   - Set deadline for full migration
   - Disable password authentication
   - Revoke non-SSO sessions

---

**Last Updated**: November 16, 2025  
**Version**: 1.0.0-beta  
**Support**: sso-support@janua.dev
