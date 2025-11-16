/**
 * Test data fixtures for Enterprise E2E tests (SSO and Invitations)
 */

// ============================================================================
// SSO Provider Test Data
// ============================================================================

export const SSO_PROVIDERS = {
  googleWorkspace: {
    name: 'Google Workspace Test',
    type: 'saml' as const,
    entityId: 'https://accounts.google.com/o/saml2',
    metadataUrl: 'https://accounts.google.com/o/saml2/idp?idpid=test123',
    enabled: true,
    jitEnabled: true,
    defaultRole: 'member',
  },
  azureAD: {
    name: 'Azure AD Test',
    type: 'saml' as const,
    entityId: 'https://sts.windows.net/tenant-id/',
    metadataUrl: 'https://login.microsoftonline.com/tenant-id/federationmetadata/2007-06/federationmetadata.xml',
    enabled: true,
    jitEnabled: true,
    defaultRole: 'member',
  },
  okta: {
    name: 'Okta Test',
    type: 'saml' as const,
    entityId: 'http://www.okta.com/exk123',
    metadataUrl: 'https://dev-123.okta.com/app/exk123/sso/saml/metadata',
    enabled: true,
    jitEnabled: false,
    defaultRole: 'admin',
  },
  oidcProvider: {
    name: 'OIDC Provider Test',
    type: 'oidc' as const,
    clientId: 'test-client-id',
    clientSecret: 'test-client-secret',
    issuer: 'https://auth.example.com',
    enabled: false,
    jitEnabled: true,
    defaultRole: 'member',
  },
  disabledProvider: {
    name: 'Disabled Provider Test',
    type: 'saml' as const,
    entityId: 'https://disabled.example.com',
    metadataUrl: 'https://disabled.example.com/metadata',
    enabled: false,
    jitEnabled: false,
  },
}

export const SAML_CONFIGS = {
  standard: {
    samlEntityId: 'https://plinto.dev/sp',
    samlAcsUrl: 'https://plinto.dev/api/v1/sso/saml/acs',
    signRequests: true,
    wantAssertionsSigned: true,
    nameIdFormat: 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
  },
  advanced: {
    samlEntityId: 'https://plinto.dev/sp',
    samlAcsUrl: 'https://plinto.dev/api/v1/sso/saml/acs',
    signRequests: false,
    wantAssertionsSigned: false,
    nameIdFormat: 'urn:oasis:names:tc:SAML:2.0:nameid-format:persistent',
    attributeMapping: {
      email: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
      firstName: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
      lastName: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
      phone: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/mobilephone',
    },
  },
}

export const SSO_TEST_RESULTS = {
  success: {
    success: true,
    testType: 'full',
    results: {
      metadataValid: true,
      certificateValid: true,
      endpointsReachable: true,
      authenticationSuccessful: true,
      userAttributes: {
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User',
      },
    },
  },
  metadataFailure: {
    success: false,
    testType: 'metadata',
    results: {
      metadataValid: false,
      errors: ['Metadata URL unreachable', 'Invalid XML format'],
    },
  },
  certificateFailure: {
    success: false,
    testType: 'full',
    results: {
      metadataValid: true,
      certificateValid: false,
      errors: ['Certificate expired', 'Invalid signature'],
    },
  },
}

// ============================================================================
// Invitation Test Data
// ============================================================================

export const TEST_INVITATIONS = {
  memberInvite: {
    email: 'new.member@plinto.dev',
    role: 'member' as const,
    message: 'Welcome to our team!',
    expiresIn: 7,
  },
  adminInvite: {
    email: 'new.admin@plinto.dev',
    role: 'admin' as const,
    message: 'Welcome as an administrator!',
    expiresIn: 14,
  },
  ownerInvite: {
    email: 'new.owner@plinto.dev',
    role: 'owner' as const,
    message: 'Welcome as an owner!',
    expiresIn: 30,
  },
  shortExpiry: {
    email: 'quick@plinto.dev',
    role: 'member' as const,
    message: 'Quick onboarding',
    expiresIn: 1, // 1 day
  },
  noMessage: {
    email: 'no.message@plinto.dev',
    role: 'member' as const,
    expiresIn: 7,
  },
  invalidEmail: {
    email: 'invalid-email',
    role: 'member' as const,
    message: 'This should fail',
    expiresIn: 7,
  },
}

export const BULK_INVITATIONS = {
  valid: [
    { email: 'bulk1@plinto.dev', role: 'member', message: 'Welcome bulk user 1!' },
    { email: 'bulk2@plinto.dev', role: 'admin', message: 'Welcome bulk user 2!' },
    { email: 'bulk3@plinto.dev', role: 'member', message: 'Welcome bulk user 3!' },
    { email: 'bulk4@plinto.dev', role: 'member', message: 'Welcome bulk user 4!' },
    { email: 'bulk5@plinto.dev', role: 'admin', message: 'Welcome bulk user 5!' },
  ],
  mixedValid: [
    { email: 'valid1@plinto.dev', role: 'member', message: 'Valid user 1' },
    { email: 'invalid-email', role: 'member', message: 'Invalid email format' },
    { email: 'valid2@plinto.dev', role: 'admin', message: 'Valid user 2' },
    { email: '@nolocal.com', role: 'member', message: 'Invalid email format' },
    { email: 'valid3@plinto.dev', role: 'member', message: 'Valid user 3' },
  ],
  tooMany: Array.from({ length: 105 }, (_, i) => ({
    email: `bulk${i + 1}@plinto.dev`,
    role: 'member',
    message: `Bulk user ${i + 1}`,
  })),
  duplicates: [
    { email: 'duplicate@plinto.dev', role: 'member', message: 'First invite' },
    { email: 'duplicate@plinto.dev', role: 'admin', message: 'Duplicate invite' },
    { email: 'unique@plinto.dev', role: 'member', message: 'Unique invite' },
  ],
}

export const INVITATION_STATUSES = {
  pending: 'pending',
  accepted: 'accepted',
  expired: 'expired',
  revoked: 'revoked',
} as const

export const INVITATION_ROLES = {
  member: 'member',
  admin: 'admin',
  owner: 'owner',
} as const

// ============================================================================
// Test Organizations
// ============================================================================

export const TEST_ENTERPRISE_ORGS = {
  techCorp: {
    id: 'org-tech-corp-123',
    name: 'Tech Corp Enterprise',
    slug: 'tech-corp-ent',
    ssoEnabled: true,
    invitationsEnabled: true,
  },
  startupInc: {
    id: 'org-startup-inc-456',
    name: 'Startup Inc',
    slug: 'startup-inc',
    ssoEnabled: false,
    invitationsEnabled: true,
  },
  enterpriseCo: {
    id: 'org-enterprise-789',
    name: 'Enterprise Co',
    slug: 'enterprise-co',
    ssoEnabled: true,
    invitationsEnabled: true,
  },
}

// ============================================================================
// Test Users for Invitation Acceptance
// ============================================================================

export const INVITATION_ACCEPTANCE_USERS = {
  newUser: {
    name: 'New Invited User',
    email: 'newinvited@plinto.dev',
    password: 'NewInvited123!',
    isNewUser: true,
  },
  existingUser: {
    email: 'existing@plinto.dev',
    password: 'Existing123!',
    isNewUser: false,
  },
  weakPassword: {
    name: 'Weak Password User',
    email: 'weak@plinto.dev',
    password: '123', // Should fail validation
    isNewUser: true,
  },
}

// ============================================================================
// CSV Test Data
// ============================================================================

export const CSV_TEST_DATA = {
  validCSV: `email,role,message
member1@plinto.dev,member,Welcome to the team!
admin1@plinto.dev,admin,Welcome as admin!
member2@plinto.dev,member,Excited to have you join us`,

  invalidFormatCSV: `no,header,row
user@plinto.dev,member,message`,

  missingEmailCSV: `email,role,message
,member,No email provided
valid@plinto.dev,admin,Valid entry`,

  invalidEmailsCSV: `email,role,message
invalid-email,member,Invalid format
@nodomain.com,admin,Invalid format
valid@plinto.dev,member,Valid entry`,

  tooManyCSV: Array.from(
    { length: 105 },
    (_, i) => `user${i + 1}@plinto.dev,member,Message ${i + 1}`
  ).join('\n'),

  emptyCSV: `email,role,message`,

  duplicateEmailsCSV: `email,role,message
duplicate@plinto.dev,member,First
duplicate@plinto.dev,admin,Second
unique@plinto.dev,member,Third`,
}

// ============================================================================
// Error Messages
// ============================================================================

export const ERROR_MESSAGES = {
  sso: {
    invalidEntityId: 'Invalid Entity ID format',
    invalidMetadataUrl: 'Invalid metadata URL',
    providerExists: 'Provider with this name already exists',
    metadataUnreachable: 'Metadata URL unreachable',
    certificateExpired: 'Certificate expired',
    certificateInvalid: 'Invalid certificate',
  },
  invitations: {
    invalidEmail: 'Invalid email address',
    emailExists: 'User with this email already exists',
    tooManyInvitations: 'Maximum 100 invitations per batch',
    invalidRole: 'Invalid role specified',
    expiryTooShort: 'Expiration must be at least 1 day',
    expiryTooLong: 'Expiration cannot exceed 30 days',
    invitationExpired: 'This invitation has expired',
    invitationRevoked: 'This invitation has been revoked',
    invitationNotFound: 'Invitation not found',
  },
  bulkUpload: {
    noFile: 'Please select a file to upload',
    invalidFormat: 'Invalid CSV format',
    missingHeader: 'CSV must contain email column',
    emptyFile: 'CSV file is empty',
    tooLarge: 'File size exceeds maximum limit',
  },
}

// ============================================================================
// Success Messages
// ============================================================================

export const SUCCESS_MESSAGES = {
  sso: {
    providerCreated: 'SSO provider created successfully',
    providerUpdated: 'SSO provider updated successfully',
    providerDeleted: 'SSO provider deleted successfully',
    testSuccess: 'SSO test completed successfully',
    configSaved: 'SAML configuration saved successfully',
  },
  invitations: {
    invitationSent: 'Invitation sent successfully',
    invitationResent: 'Invitation resent successfully',
    invitationRevoked: 'Invitation revoked successfully',
    bulkSent: 'Bulk invitations sent successfully',
    invitationAccepted: 'Invitation accepted successfully',
  },
}
