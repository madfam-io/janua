# SCIM Provisioning Guide

**Version**: 1.0.0-beta  
**Last Updated**: November 16, 2025  
**Protocol**: SCIM 2.0 (RFC 7644)  
**Applies to**: Enterprise Plan

> [!NOTE]
> **Claim status: Roadmap.** Per the
> [GA claim matrix](../enterprise/GA_CLAIM_MATRIX.md), SCIM provisioning must
> not be sold as available until create/update/deactivate synthetics and
> monitoring are in place. This guide documents the in-repo implementation for
> design partners and self-hosters evaluating it at their own risk.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Getting Started](#getting-started)
4. [Supported Providers](#supported-providers)
5. [SCIM Endpoints](#scim-endpoints)
6. [User Provisioning](#user-provisioning)
7. [Group Provisioning](#group-provisioning)
8. [Provider-Specific Setup](#provider-specific-setup)
9. [Testing & Validation](#testing--validation)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)

---

## Overview

SCIM (System for Cross-domain Identity Management) 2.0 automates user provisioning and deprovisioning between your identity provider and Janua.

### What is SCIM?

SCIM is a standardized REST API protocol that enables:
- **Automatic User Creation**: New users in your IdP automatically get Janua accounts
- **Real-time Updates**: User changes sync instantly
- **Automatic Deprovisioning**: Removing users from IdP removes Janua access
- **Group Management**: Sync organizational structure and teams

### Benefits

✅ **Zero Manual Provisioning**: Eliminate manual account creation  
✅ **Real-time Sync**: Changes propagate in seconds, not hours  
✅ **Enhanced Security**: Immediately revoke access when users leave  
✅ **Reduced IT Burden**: Automate 90% of user management tasks  
✅ **Compliance**: Maintain accurate user records automatically  

### How It Works

```
┌──────────────┐         SCIM 2.0 API         ┌─────────────┐
│   Identity   │────────────────────────────▶│   Janua    │
│   Provider   │                              │             │
│   (IdP)      │◀────────────────────────────│             │
└──────────────┘                              └─────────────┘
     │                                              │
     │  1. User created/updated/deleted            │
     │  2. IdP sends SCIM request                  │
     │  3. Janua validates & processes            │
     │  4. Returns success/error response          │
     │  5. IdP updates sync status                 │
     └──────────────────────────────────────────────┘
```

### SCIM vs SSO

| Feature | SCIM | SSO |
|---------|------|-----|
| **Purpose** | User provisioning | Authentication |
| **When** | Before login | During login |
| **What** | Create/update/delete accounts | Verify identity |
| **Use Together** | ✅ Recommended | ✅ Recommended |

**Best Practice**: Use SCIM + SSO together for complete automation

---

## Prerequisites

### Requirements

- ✅ **Enterprise Plan**: SCIM is available on Enterprise plan only
- ✅ **Organization Admin**: Administrative access to Janua
- ✅ **IdP Admin**: Access to configure SCIM in your identity provider
- ✅ **Verified Domain**: Domain ownership verified in Janua
- ✅ **SSO Configured**: SSO should be set up first (recommended)

### Supported Features

Janua's SCIM implementation supports:

| Feature | Support | Notes |
|---------|---------|-------|
| **User Create** | ✅ Full | Create new user accounts |
| **User Read** | ✅ Full | Retrieve user details |
| **User Update** | ✅ Full | Update user attributes |
| **User Delete** | ✅ Full | Deactivate user accounts |
| **User Replace** | ✅ Full | Full user replacement |
| **Group Create** | ✅ Full | Create groups/teams |
| **Group Read** | ✅ Full | Retrieve group details |
| **Group Update** | ✅ Full | Update group membership |
| **Group Delete** | ✅ Full | Delete groups |
| **Filtering** | ✅ Partial | User and group filtering |
| **Pagination** | ✅ Full | Large dataset support |
| **Bulk Operations** | ⚠️ Limited | Batch user operations |
| **Schema Discovery** | ✅ Full | /Schemas endpoint |

---

## Getting Started

### Step 1: Generate SCIM Credentials

1. **Navigate to SCIM Settings**
   - Go to Organization Settings → Security → SCIM Provisioning
   - Click "Enable SCIM"

2. **Generate Bearer Token**
   - Click "Generate New Token"
   - **IMPORTANT**: Copy token immediately (shown only once)
   - Store securely (1Password, Vault, etc.)

3. **Copy SCIM Endpoint**
   ```
   SCIM Base URL:
   https://api.janua.dev/scim/v2
   
   Organization-Specific URL:
   https://api.janua.dev/scim/v2?org={organization_id}
   ```

### Step 2: Test SCIM Connection

Use curl to verify SCIM endpoint:

```bash
# Test ServiceProviderConfig endpoint
curl -X GET \
  'https://api.janua.dev/scim/v2/ServiceProviderConfig' \
  -H 'Authorization: Bearer {your_scim_token}' \
  -H 'Content-Type: application/scim+json'

# Expected response
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
  "documentationUri": "https://docs.janua.dev/scim",
  "patch": {
    "supported": true
  },
  "bulk": {
    "supported": true,
    "maxOperations": 100,
    "maxPayloadSize": 1048576
  },
  "filter": {
    "supported": true,
    "maxResults": 200
  },
  "changePassword": {
    "supported": false
  },
  "sort": {
    "supported": true
  },
  "etag": {
    "supported": true
  },
  "authenticationSchemes": [
    {
      "type": "oauthbearertoken",
      "name": "OAuth Bearer Token",
      "description": "Authentication scheme using the OAuth Bearer Token",
      "specUri": "http://www.rfc-editor.org/info/rfc6750",
      "documentationUri": "https://docs.janua.dev/scim/authentication"
    }
  ]
}
```

### Step 3: Configure IdP

Proceed to [Provider-Specific Setup](#provider-specific-setup) for your identity provider.

---

## SCIM Endpoints

### Base URL

```
https://api.janua.dev/scim/v2
```

### Authentication

All requests require Bearer token authentication:

```http
Authorization: Bearer {scim_token}
Content-Type: application/scim+json
```

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ServiceProviderConfig` | GET | Get SCIM capabilities |
| `/Schemas` | GET | List supported schemas |
| `/ResourceTypes` | GET | List resource types |
| `/Users` | GET, POST | List and create users |
| `/Users/{id}` | GET, PUT, PATCH, DELETE | Manage specific user |
| `/Groups` | GET, POST | List and create groups |
| `/Groups/{id}` | GET, PUT, PATCH, DELETE | Manage specific group |

---

## User Provisioning

### User Schema

```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "externalId": "user@example.com",
  "userName": "user@example.com",
  "name": {
    "formatted": "John Doe",
    "familyName": "Doe",
    "givenName": "John"
  },
  "emails": [
    {
      "value": "user@example.com",
      "primary": true
    }
  ],
  "active": true,
  "groups": [
    {
      "value": "group_123",
      "display": "Engineering"
    }
  ],
  "meta": {
    "resourceType": "User",
    "created": "2025-01-15T10:30:00Z",
    "lastModified": "2025-11-16T14:22:00Z",
    "location": "https://api.janua.dev/scim/v2/Users/123e4567-e89b-12d3-a456-426614174000"
  }
}
```

### Create User

**Request:**
```http
POST /scim/v2/Users
Authorization: Bearer {token}
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "newuser@example.com",
  "name": {
    "givenName": "Jane",
    "familyName": "Smith"
  },
  "emails": [
    {
      "value": "newuser@example.com",
      "primary": true
    }
  ],
  "active": true
}
```

**Response (201 Created):**
```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "externalId": "newuser@example.com",
  "userName": "newuser@example.com",
  "name": {
    "formatted": "Jane Smith",
    "familyName": "Smith",
    "givenName": "Jane"
  },
  "emails": [
    {
      "value": "newuser@example.com",
      "primary": true
    }
  ],
  "active": true,
  "meta": {
    "resourceType": "User",
    "created": "2025-11-16T15:45:00Z",
    "lastModified": "2025-11-16T15:45:00Z",
    "location": "https://api.janua.dev/scim/v2/Users/456e7890-e89b-12d3-a456-426614174001"
  }
}
```

### Get User

**Request:**
```http
GET /scim/v2/Users/{id}
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "userName": "user@example.com",
  ...
}
```

### List Users

**Request:**
```http
GET /scim/v2/Users?startIndex=1&count=100
Authorization: Bearer {token}
```

**With Filter:**
```http
GET /scim/v2/Users?filter=userName eq "user@example.com"
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
  "totalResults": 150,
  "startIndex": 1,
  "itemsPerPage": 100,
  "Resources": [
    {
      "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "userName": "user@example.com",
      ...
    }
  ]
}
```

### Update User (PUT)

**Request:**
```http
PUT /scim/v2/Users/{id}
Authorization: Bearer {token}
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "userName": "user@example.com",
  "name": {
    "givenName": "John",
    "familyName": "Doe-Smith"
  },
  "emails": [
    {
      "value": "user@example.com",
      "primary": true
    }
  ],
  "active": true
}
```

### Update User (PATCH)

**Request:**
```http
PATCH /scim/v2/Users/{id}
Authorization: Bearer {token}
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {
      "op": "replace",
      "path": "name.familyName",
      "value": "Doe-Smith"
    },
    {
      "op": "replace",
      "path": "active",
      "value": false
    }
  ]
}
```

### Deactivate User

**Request:**
```http
PATCH /scim/v2/Users/{id}
Authorization: Bearer {token}
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {
      "op": "replace",
      "path": "active",
      "value": false
    }
  ]
}
```

Or DELETE:
```http
DELETE /scim/v2/Users/{id}
Authorization: Bearer {token}
```

---

## Group Provisioning

### Group Schema

```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
  "id": "group_123",
  "displayName": "Engineering",
  "members": [
    {
      "value": "123e4567-e89b-12d3-a456-426614174000",
      "$ref": "https://api.janua.dev/scim/v2/Users/123e4567-e89b-12d3-a456-426614174000",
      "display": "John Doe"
    },
    {
      "value": "456e7890-e89b-12d3-a456-426614174001",
      "$ref": "https://api.janua.dev/scim/v2/Users/456e7890-e89b-12d3-a456-426614174001",
      "display": "Jane Smith"
    }
  ],
  "meta": {
    "resourceType": "Group",
    "created": "2025-01-15T10:30:00Z",
    "lastModified": "2025-11-16T15:45:00Z",
    "location": "https://api.janua.dev/scim/v2/Groups/group_123"
  }
}
```

### Create Group

**Request:**
```http
POST /scim/v2/Groups
Authorization: Bearer {token}
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
  "displayName": "Product Team",
  "members": []
}
```

### Add User to Group

**Request:**
```http
PATCH /scim/v2/Groups/{group_id}
Authorization: Bearer {token}
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {
      "op": "add",
      "path": "members",
      "value": [
        {
          "value": "123e4567-e89b-12d3-a456-426614174000"
        }
      ]
    }
  ]
}
```

### Remove User from Group

**Request:**
```http
PATCH /scim/v2/Groups/{group_id}
Authorization: Bearer {token}
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {
      "op": "remove",
      "path": "members[value eq \"123e4567-e89b-12d3-a456-426614174000\"]"
    }
  ]
}
```

---

## Provider-Specific Setup

### Okta

#### Setup Steps

1. **Navigate to Applications**
   - Admin Console → Applications → Applications
   - Click "Browse App Catalog"

2. **Add SCIM Application**
   - Search for "SCIM 2.0 Test App (Header Auth)"
   - Or create custom SCIM app

3. **Configure SCIM Connection**
   - Provisioning tab → Configure API Integration
   - Enable API integration
   
   ```
   SCIM 2.0 Base URL:
   https://api.janua.dev/scim/v2
   
   Unique identifier field: userName
   
   Supported provisioning actions:
   - Push New Users
   - Push Profile Updates
   - Push Groups
   
   Authentication Mode: HTTP Header
   Authorization: Bearer {your_scim_token}
   ```

4. **Configure Attribute Mappings**
   - To App tab:
     ```
     userName → userName
     email → emails[0].value
     givenName → name.givenName
     familyName → name.familyName
     ```

5. **Test Connection**
   - Click "Test API Credentials"
   - Should see "Success" message

6. **Enable Provisioning**
   - Provisioning tab → Settings
   - Enable:
     - Create Users
     - Update User Attributes
     - Deactivate Users
   - Save

7. **Assign Users/Groups**
   - Assignments tab → Assign → Assign to People/Groups
   - Users will be automatically created in Janua

#### Okta-Specific Settings

**Group Push**:
- Navigate to Push Groups tab
- Click "Push Groups" → Find groups by name
- Select groups to sync
- Members will be added to corresponding Janua groups

**Sync Schedule**:
- Default: Real-time for user changes
- Group sync: Every 24 hours (can be manual)

---

### Azure AD / Microsoft Entra ID

#### Setup Steps

1. **Add Enterprise Application**
   - Azure Portal → Entra ID → Enterprise applications
   - New application → Create your own application
   - Name: Janua SCIM
   - Integrate any other application (non-gallery)

2. **Configure Provisioning**
   - Provisioning → Automatic
   
   ```
   Tenant URL:
   https://api.janua.dev/scim/v2
   
   Secret Token:
   {your_scim_token}
   ```

3. **Test Connection**
   - Click "Test Connection"
   - Should see "The supplied credentials are authorized"

4. **Configure Attribute Mappings**
   - Mappings → Provision Azure Active Directory Users
   
   | Azure AD Attribute | SCIM Attribute |
   |--------------------|----------------|
   | userPrincipalName | userName |
   | mail | emails[type eq "work"].value |
   | givenName | name.givenName |
   | surname | name.familyName |
   | accountEnabled | active |

5. **Configure Group Mappings** (optional)
   - Mappings → Provision Azure Active Directory Groups
   
   | Azure AD Attribute | SCIM Attribute |
   |--------------------|----------------|
   | displayName | displayName |
   | members | members |

6. **Set Scope**
   - Settings → Scope
   - Choose:
     - Sync only assigned users and groups (recommended)
     - Sync all users and groups

7. **Enable Provisioning**
   - Settings → Provisioning Status → On
   - Save

8. **Monitor Provisioning**
   - Provisioning logs → View sync status
   - Check for errors

#### Azure-Specific Settings

**Sync Interval**:
- Default: 40 minutes
- Can trigger manual sync: Provisioning → Restart provisioning

**Notifications**:
- Settings → Notification → Email for failures

---

### Google Workspace

#### Setup Steps

1. **Enable Custom SCIM Application**
   - Admin Console → Apps → Web and mobile apps
   - Add app → Add custom SCIM app

2. **Configure Application**
   - App name: Janua
   
   ```
   SCIM endpoint URL:
   https://api.janua.dev/scim/v2
   
   Authorization type: Bearer token
   Access token: {your_scim_token}
   ```

3. **Attribute Mapping**
   - Basic mapping (auto-configured):
     ```
     Primary email → userName
     First name → name.givenName
     Last name → name.familyName
     ```

4. **Test Connection**
   - Click "Test connection"
   - Should see "Connection successful"

5. **Enable Provisioning**
   - User provisioning → On
   - Choose org units to sync

6. **Configure Deprovisioning**
   - Deprovisioning → Suspend or delete users
   - Recommended: Suspend (sets active=false)

#### Google-Specific Settings

**Group Sync**:
- Google Admin SDK groups map to Janua groups
- Configure in Group provisioning settings

**Sync Frequency**:
- Real-time for user create/update/delete
- Group sync: Every 24 hours

---

### OneLogin

#### Setup Steps

1. **Add SCIM Application**
   - Applications → Add App
   - Search: "SCIM Provisioner with SAML"
   - Or: "SCIM 2.0"

2. **Configure SCIM**
   - Configuration tab:
   
   ```
   SCIM Base URL:
   https://api.janua.dev/scim/v2
   
   SCIM Bearer Token:
   {your_scim_token}
   
   SCIM JSON Template:
   {
     "userName": "{$parameters.scimusername}",
     "name": {
       "givenName": "{$user.firstname}",
       "familyName": "{$user.lastname}"
     },
     "emails": [{
       "value": "{$user.email}",
       "primary": true
     }],
     "active": true
   }
   ```

3. **Enable Provisioning**
   - Provisioning tab → Enable provisioning
   - Check:
     - Create user
     - Delete user
     - Update user

4. **Assign Users**
   - Users tab → Add users

---

## Testing & Validation

### Test Checklist

- [ ] **SCIM Endpoint Accessible**
  - Test GET /ServiceProviderConfig
  - Verify authentication works

- [ ] **User Provisioning**
  - Create test user in IdP
  - Verify user appears in Janua
  - Check all attributes mapped correctly

- [ ] **User Updates**
  - Update user name in IdP
  - Verify change syncs to Janua
  - Check update timestamp

- [ ] **User Deprovisioning**
  - Disable/delete user in IdP
  - Verify user deactivated in Janua
  - Check access revoked

- [ ] **Group Sync** (if enabled)
  - Create group in IdP
  - Add users to group
  - Verify group and members in Janua

### Manual Testing

#### 1. Test User Creation

```bash
# Create user via SCIM API
curl -X POST 'https://api.janua.dev/scim/v2/Users' \
  -H 'Authorization: Bearer {token}' \
  -H 'Content-Type: application/scim+json' \
  -d '{
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "userName": "testuser@example.com",
    "name": {
      "givenName": "Test",
      "familyName": "User"
    },
    "emails": [{
      "value": "testuser@example.com",
      "primary": true
    }],
    "active": true
  }'
```

#### 2. Test User Retrieval

```bash
# Get user by ID
curl -X GET 'https://api.janua.dev/scim/v2/Users/{user_id}' \
  -H 'Authorization: Bearer {token}'

# Filter by userName
curl -X GET 'https://api.janua.dev/scim/v2/Users?filter=userName eq "testuser@example.com"' \
  -H 'Authorization: Bearer {token}'
```

#### 3. Test User Update

```bash
# Update user
curl -X PATCH 'https://api.janua.dev/scim/v2/Users/{user_id}' \
  -H 'Authorization: Bearer {token}' \
  -H 'Content-Type: application/scim+json' \
  -d '{
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
    "Operations": [{
      "op": "replace",
      "path": "name.familyName",
      "value": "NewLastName"
    }]
  }'
```

#### 4. Test User Deactivation

```bash
# Deactivate user
curl -X PATCH 'https://api.janua.dev/scim/v2/Users/{user_id}' \
  -H 'Authorization: Bearer {token}' \
  -H 'Content-Type: application/scim+json' \
  -d '{
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
    "Operations": [{
      "op": "replace",
      "path": "active",
      "value": false
    }]
  }'
```

### Monitoring Sync Status

#### Janua SCIM Dashboard

1. **Navigate to SCIM Logs**
   - Organization Settings → SCIM Provisioning → Sync Logs

2. **View Sync Events**
   - Filter by event type (create, update, delete)
   - Filter by user email
   - Filter by date range

3. **Check Sync Statistics**
   ```
   Last 24 Hours:
   - Users Created: 15
   - Users Updated: 42
   - Users Deactivated: 3
   - Groups Synced: 8
   - Errors: 0
   ```

#### IdP Sync Logs

Check your IdP's provisioning logs for detailed sync status and errors.

---

## Troubleshooting

### Common Issues

#### 1. Authentication Failure

**Error**: `401 Unauthorized`

**Causes**:
- Invalid bearer token
- Token expired
- Token not in Authorization header

**Solutions**:
```bash
# Verify token format
Authorization: Bearer abc123def456...

# NOT
Authorization: abc123def456...
Authorization: Token abc123def456...
```

- Regenerate token in Janua settings
- Verify no extra spaces in header

#### 2. User Already Exists

**Error**: `409 Conflict - User already exists`

**Causes**:
- User with same email already exists
- Duplicate externalId

**Solutions**:
- Check if user exists: GET /Users?filter=userName eq "email"
- Use PATCH instead of POST to update
- Ensure IdP sends unique userNames

#### 3. Invalid Attribute

**Error**: `400 Bad Request - Invalid attribute`

**Causes**:
- Required attribute missing
- Attribute format incorrect
- Unsupported attribute

**Solutions**:
- Check required attributes: userName, emails[0].value, name.givenName, name.familyName
- Verify attribute mapping in IdP
- Check SCIM schema: GET /Schemas

#### 4. Slow Sync

**Issue**: Users not syncing in real-time

**Causes**:
- IdP sync interval too long
- Large batch of changes
- Network issues

**Solutions**:
- Check IdP sync schedule
- Trigger manual sync
- Monitor network latency
- Check SCIM logs for errors

#### 5. Group Sync Not Working

**Issue**: Groups not syncing to Janua

**Causes**:
- Group provisioning not enabled
- Incorrect group mapping
- Group membership not updated

**Solutions**:
- Enable group provisioning in IdP
- Verify group attribute mapping
- Check group push settings (Okta)
- Manually trigger group sync

---

## Best Practices

### 1. Token Management

✅ **Do:**
- Store token securely (never in code)
- Rotate tokens every 90 days
- Use separate tokens for dev/staging/prod
- Monitor token usage

❌ **Don't:**
- Commit tokens to Git
- Share tokens between environments
- Use same token for multiple orgs

### 2. Provisioning Strategy

✅ **Do:**
- Start with pilot group
- Test thoroughly before full rollout
- Enable deprovisioning gradually
- Monitor sync logs daily

❌ **Don't:**
- Enable for entire org immediately
- Skip testing phase
- Ignore sync errors

### 3. Attribute Mapping

✅ **Do:**
- Map all required attributes
- Use consistent field names
- Document custom mappings
- Test edge cases (special characters, long names)

❌ **Don't:**
- Leave required fields unmapped
- Use hardcoded values
- Assume default mappings work

### 4. Error Handling

✅ **Do:**
- Set up error notifications
- Review logs weekly
- Have rollback plan
- Document common issues

❌ **Don't:**
- Ignore failed syncs
- Assume sync always works
- Skip error monitoring

### 5. Security

✅ **Do:**
- Use HTTPS only
- Implement IP allowlisting (if possible)
- Audit SCIM activity
- Require MFA for SCIM admins

❌ **Don't:**
- Use HTTP
- Expose SCIM token
- Skip security reviews
- Allow unrestricted access

---

## Advanced Configuration

### Custom Attributes

Map custom IdP attributes to Janua:

```json
{
  "schemas": [
    "urn:ietf:params:scim:schemas:core:2.0:User",
    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
  ],
  "userName": "user@example.com",
  "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
    "employeeNumber": "12345",
    "department": "Engineering",
    "manager": {
      "value": "manager_user_id",
      "displayName": "Jane Manager"
    }
  }
}
```

### Filtering

SCIM supports filtering for efficient queries:

```
# Filter by userName
GET /Users?filter=userName eq "user@example.com"

# Filter by active status
GET /Users?filter=active eq true

# Complex filter
GET /Users?filter=userName sw "john" and active eq true

# Filter groups by displayName
GET /Groups?filter=displayName co "Engineering"
```

### Pagination

Handle large datasets with pagination:

```
# First page
GET /Users?startIndex=1&count=100

# Second page
GET /Users?startIndex=101&count=100
```

---

## Migration from Manual Provisioning

### Pre-Migration Checklist

- [ ] Audit existing users
- [ ] Clean up duplicate accounts
- [ ] Verify email addresses match IdP
- [ ] Document custom roles/permissions
- [ ] Backup user data

### Migration Steps

1. **Pilot Phase**
   - Select 10-20 test users
   - Enable SCIM for pilot group
   - Monitor for 1 week

2. **Gradual Rollout**
   - Enable for 25% of users
   - Monitor for issues
   - Increase to 50%, then 100%

3. **Full Migration**
   - Enable SCIM for all users
   - Disable manual provisioning
   - Update documentation

4. **Post-Migration**
   - Monitor sync logs
   - Address any issues
   - Gather feedback

---

## Support & Resources

- **Documentation**: https://docs.janua.dev/scim
- **SCIM 2.0 Spec**: https://datatracker.ietf.org/doc/html/rfc7644
- **Community Forum**: https://community.janua.dev
- **Email Support**: scim-support@janua.dev
- **Enterprise Support**: Available 24/7

---

**Last Updated**: November 16, 2025  
**Version**: 1.0.0-beta  
**Support**: scim-support@janua.dev
