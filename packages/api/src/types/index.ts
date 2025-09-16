import { User, Tenant, Team, Session, PaymentCustomer, BillingSubscription, AuditLog } from '@prisma/client';
import { Request } from 'express';
import { JwtPayload } from 'jsonwebtoken';

// =============================================================================
// REQUEST CONTEXT TYPES
// =============================================================================

export interface AuthenticatedUser extends User {
  tenant: Tenant;
}

export interface RequestContext {
  tenant: Tenant;
  user?: AuthenticatedUser;
  session?: Session;
  requestId: string;
  userAgent?: string;
  ipAddress?: string;
  permissions: string[];
  roles: string[];
}

export interface AuthenticatedRequest extends Request {
  context: RequestContext;
  user: AuthenticatedUser;
}

export interface TenantRequest extends Request {
  context: RequestContext;
}

// =============================================================================
// JWT & AUTH TYPES
// =============================================================================

export interface JwtTokenPayload extends JwtPayload {
  userId: string;
  tenantId: string;
  sessionId: string;
  type: 'access' | 'refresh';
  permissions?: string[];
  roles?: string[];
}

export interface LoginCredentials {
  email: string;
  password: string;
  tenantSlug?: string;
  mfaToken?: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  tenantName?: string;
  tenantSlug?: string;
}

export interface MfaSetupData {
  secret: string;
  qrCode: string;
  backupCodes: string[];
}

export interface WebAuthnRegistrationData {
  challenge: string;
  user: {
    id: string;
    name: string;
    displayName: string;
  };
  rp: {
    name: string;
    id: string;
  };
  pubKeyCredParams: Array<{
    type: 'public-key';
    alg: number;
  }>;
  authenticatorSelection: {
    authenticatorAttachment?: 'platform' | 'cross-platform';
    userVerification: 'required' | 'preferred' | 'discouraged';
    residentKey?: 'required' | 'preferred' | 'discouraged';
  };
  timeout: number;
  attestation: 'none' | 'indirect' | 'direct';
}

// =============================================================================
// USER MANAGEMENT TYPES
// =============================================================================

export interface UserProfile {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  displayName?: string;
  avatarUrl?: string;
  phone?: string;
  language: string;
  timezone: string;
  preferences: Record<string, any>;
  mfaEnabled: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface UpdateUserProfile {
  firstName?: string;
  lastName?: string;
  displayName?: string;
  phone?: string;
  language?: string;
  timezone?: string;
  preferences?: Record<string, any>;
}

export interface ChangePasswordData {
  currentPassword: string;
  newPassword: string;
}

// =============================================================================
// TEAM MANAGEMENT TYPES
// =============================================================================

export interface TeamData {
  name: string;
  slug: string;
  description?: string;
  parentTeamId?: string;
  settings?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface TeamMemberData {
  userId: string;
  role: 'owner' | 'lead' | 'member' | 'viewer' | 'guest';
  permissions?: string[];
  isLead?: boolean;
}

export interface TeamInvitationData {
  email: string;
  role: string;
  permissions?: string[];
  message?: string;
  expiresInDays?: number;
}

export interface TeamWithMembers extends Team {
  members: Array<{
    id: string;
    role: string;
    permissions: string[];
    isLead: boolean;
    joinedAt: Date;
    user: {
      id: string;
      email: string;
      firstName?: string;
      lastName?: string;
      displayName?: string;
      avatarUrl?: string;
    };
  }>;
  _count: {
    members: number;
    projects: number;
  };
}

// =============================================================================
// PAYMENT TYPES
// =============================================================================

export interface PaymentMethodData {
  type: 'card' | 'bank_transfer' | 'digital_wallet';
  provider: 'stripe' | 'conekta' | 'fungies';
  cardDetails?: {
    number: string;
    expMonth: number;
    expYear: number;
    cvc: string;
  };
  bankDetails?: {
    accountNumber: string;
    routingNumber: string;
    accountType: 'checking' | 'savings';
  };
  walletDetails?: {
    type: 'apple_pay' | 'google_pay' | 'paypal';
    token: string;
  };
  billingAddress?: {
    line1: string;
    line2?: string;
    city: string;
    state: string;
    postalCode: string;
    country: string;
  };
}

export interface PaymentIntentData {
  amount: number;
  currency: string;
  description?: string;
  paymentMethodId?: string;
  automaticPaymentMethods?: boolean;
  metadata?: Record<string, any>;
}

export interface CheckoutSessionData {
  amount: number;
  currency: string;
  successUrl: string;
  cancelUrl: string;
  lineItems: Array<{
    name: string;
    description?: string;
    quantity: number;
    amount: number;
  }>;
  metadata?: Record<string, any>;
}

// =============================================================================
// SUBSCRIPTION TYPES
// =============================================================================

export interface SubscriptionData {
  planId: string;
  paymentMethodId?: string;
  trialDays?: number;
  quantity?: number;
  couponId?: string;
  metadata?: Record<string, any>;
}

export interface BillingPlanData {
  name: string;
  displayName: string;
  description: string;
  priceAmount: number;
  priceCurrency: string;
  priceInterval: 'monthly' | 'yearly' | 'one-time';
  priceIntervalCount?: number;
  features: Record<string, any>;
  limits: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface SubscriptionUpdate {
  planId?: string;
  quantity?: number;
  cancelAtPeriodEnd?: boolean;
  metadata?: Record<string, any>;
}

// =============================================================================
// AUDIT & MONITORING TYPES
// =============================================================================

export interface AuditLogData {
  action: string;
  resourceType: string;
  resourceId?: string;
  resourceName?: string;
  details?: Record<string, any>;
  riskScore?: number;
  complianceFlags?: string[];
  metadata?: Record<string, any>;
}

export interface AuditLogFilter {
  actorId?: string;
  action?: string;
  resourceType?: string;
  outcome?: 'success' | 'failure' | 'error';
  dateFrom?: Date;
  dateTo?: Date;
  riskScoreMin?: number;
  riskScoreMax?: number;
  complianceFlag?: string;
  limit?: number;
  offset?: number;
}

// =============================================================================
// API RESPONSE TYPES
// =============================================================================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  metadata?: {
    pagination?: {
      page: number;
      limit: number;
      total: number;
      totalPages: number;
    };
    requestId: string;
    timestamp: string;
  };
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface PaginationResult<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// =============================================================================
// VALIDATION TYPES
// =============================================================================

export interface ValidationError {
  field: string;
  message: string;
  value?: any;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

// =============================================================================
// WEBHOOK TYPES
// =============================================================================

export interface WebhookEvent {
  id: string;
  type: string;
  data: any;
  created: number;
  livemode: boolean;
}

export interface WebhookPayload {
  event: WebhookEvent;
  signature: string;
  timestamp: number;
}

// =============================================================================
// ERROR TYPES
// =============================================================================

export class ApiError extends Error {
  public readonly statusCode: number;
  public readonly code: string;
  public readonly details?: any;

  constructor(
    statusCode: number,
    code: string,
    message: string,
    details?: any
  ) {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.name = 'ApiError';

    // Maintains proper stack trace for where error was thrown
    Error.captureStackTrace(this, ApiError);
  }
}

// =============================================================================
// CONFIGURATION TYPES
// =============================================================================

export interface DatabaseConfig {
  url: string;
  maxConnections?: number;
  connectionTimeout?: number;
  ssl?: boolean;
}

export interface RedisConfig {
  host: string;
  port: number;
  password?: string;
  db?: number;
  keyPrefix?: string;
}

export interface JwtConfig {
  accessTokenSecret: string;
  refreshTokenSecret: string;
  accessTokenExpiry: string;
  refreshTokenExpiry: string;
  issuer: string;
  audience: string;
}

export interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
  skipSuccessfulRequests?: boolean;
  skipFailedRequests?: boolean;
}

export interface EmailConfig {
  host: string;
  port: number;
  secure: boolean;
  auth: {
    user: string;
    pass: string;
  };
  from: {
    name: string;
    address: string;
  };
}

export interface PaymentProviderConfig {
  stripe?: {
    secretKey: string;
    publicKey: string;
    webhookSecret: string;
  };
  conekta?: {
    privateKey: string;
    publicKey: string;
    webhookSecret: string;
  };
  fungies?: {
    apiKey: string;
    secretKey: string;
    webhookSecret: string;
  };
}

export interface ServerConfig {
  port: number;
  host: string;
  env: 'development' | 'staging' | 'production';
  database: DatabaseConfig;
  redis: RedisConfig;
  jwt: JwtConfig;
  rateLimit: RateLimitConfig;
  email: EmailConfig;
  paymentProviders: PaymentProviderConfig;
  cors: {
    origin: string | string[];
    credentials: boolean;
  };
  monitoring: {
    enabled: boolean;
    endpoint?: string;
    apiKey?: string;
  };
}

// =============================================================================
// SERVICE TYPES
// =============================================================================

export interface ServiceResult<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface BackgroundJob {
  id: string;
  type: string;
  payload: any;
  priority: number;
  attempts: number;
  maxAttempts: number;
  delay?: number;
  scheduledAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface NotificationData {
  type: 'email' | 'sms' | 'push' | 'webhook';
  recipient: string;
  subject?: string;
  content: string;
  templateId?: string;
  templateData?: Record<string, any>;
  metadata?: Record<string, any>;
}

// =============================================================================
// EXPORT ALL TYPES
// =============================================================================

export * from '@prisma/client';