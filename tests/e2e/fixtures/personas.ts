/**
 * User Persona Factories
 * 
 * Generate realistic test data for each user persona type.
 * Ensures consistent, valid test data across all journey tests.
 */

export interface PersonaData {
  email: string;
  password: string;
  name: string;
  role: string;
  company?: string;
  metadata?: Record<string, any>;
}

/**
 * Developer Integrator Persona
 * Technical users integrating Plinto authentication
 */
export class DeveloperPersona {
  static create(overrides: Partial<PersonaData> = {}): PersonaData {
    const timestamp = Date.now();
    
    return {
      email: `developer-${timestamp}@example.com`,
      password: 'DevSecureP@ss123!',
      name: `Dev User ${timestamp}`,
      role: 'developer',
      company: 'Acme Tech Corp',
      metadata: {
        techStack: ['TypeScript', 'React', 'Node.js'],
        experience: 'senior',
        teamSize: 5,
        ...overrides.metadata
      },
      ...overrides
    };
  }

  static createBatch(count: number): PersonaData[] {
    return Array.from({ length: count }, (_, i) => 
      this.create({ 
        email: `developer-${Date.now()}-${i}@example.com` 
      })
    );
  }
}

/**
 * End User Persona
 * Application users authenticating and managing identity
 */
export class EndUserPersona {
  static create(overrides: Partial<PersonaData> = {}): PersonaData {
    const timestamp = Date.now();
    
    return {
      email: `user-${timestamp}@example.com`,
      password: 'UserSecureP@ss456!',
      name: `End User ${timestamp}`,
      role: 'end_user',
      metadata: {
        preferredAuth: 'password', // password | oauth | passkey
        mfaEnabled: false,
        deviceCount: 1,
        ...overrides.metadata
      },
      ...overrides
    };
  }

  static createWithMFA(overrides: Partial<PersonaData> = {}): PersonaData {
    return this.create({
      ...overrides,
      metadata: {
        ...overrides.metadata,
        mfaEnabled: true,
        mfaMethod: 'totp'
      }
    });
  }

  static createWithPasskey(overrides: Partial<PersonaData> = {}): PersonaData {
    return this.create({
      ...overrides,
      metadata: {
        ...overrides.metadata,
        preferredAuth: 'passkey',
        passkeyRegistered: true
      }
    });
  }
}

/**
 * Security Admin Persona
 * Security professionals managing enterprise authentication
 */
export class SecurityAdminPersona {
  static create(overrides: Partial<PersonaData> = {}): PersonaData {
    const timestamp = Date.now();
    
    return {
      email: `security-admin-${timestamp}@example.com`,
      password: 'AdminSecureP@ss789!',
      name: `Security Admin ${timestamp}`,
      role: 'security_admin',
      company: 'Enterprise Corp',
      metadata: {
        permissions: ['view_audit_logs', 'manage_policies', 'manage_users'],
        certifications: ['CISSP', 'CISM'],
        complianceNeeds: ['SOC2', 'GDPR'],
        ...overrides.metadata
      },
      ...overrides
    };
  }

  static createOrgAdmin(overrides: Partial<PersonaData> = {}): PersonaData {
    return this.create({
      ...overrides,
      metadata: {
        ...overrides.metadata,
        permissions: [
          'view_audit_logs',
          'manage_policies',
          'manage_users',
          'manage_organization',
          'manage_billing'
        ]
      }
    });
  }
}

/**
 * Business Decision Maker Persona
 * CTOs, managers evaluating and purchasing Plinto
 */
export class BusinessDecisionMakerPersona {
  static create(overrides: Partial<PersonaData> = {}): PersonaData {
    const timestamp = Date.now();
    
    return {
      email: `decision-maker-${timestamp}@example.com`,
      password: 'BizSecureP@ss012!',
      name: `CTO ${timestamp}`,
      role: 'decision_maker',
      company: 'Startup Inc',
      metadata: {
        title: 'CTO',
        companySize: 50,
        budget: 10000,
        evaluationCriteria: ['security', 'pricing', 'ease-of-use'],
        competitors: ['Auth0', 'Clerk', 'Supabase'],
        ...overrides.metadata
      },
      ...overrides
    };
  }

  static createEnterpriseDecisionMaker(overrides: Partial<PersonaData> = {}): PersonaData {
    return this.create({
      ...overrides,
      company: 'Enterprise Global Inc',
      metadata: {
        ...overrides.metadata,
        companySize: 5000,
        budget: 100000,
        evaluationCriteria: ['security', 'compliance', 'support', 'sla']
      }
    });
  }
}

/**
 * Persona Manager
 * Centralized persona lifecycle management
 */
export class PersonaManager {
  private createdPersonas: Set<string> = new Set();

  /**
   * Track created persona for cleanup
   */
  track(persona: PersonaData): PersonaData {
    this.createdPersonas.add(persona.email);
    return persona;
  }

  /**
   * Get all tracked personas
   */
  getTracked(): string[] {
    return Array.from(this.createdPersonas);
  }

  /**
   * Clear tracking
   */
  clear(): void {
    this.createdPersonas.clear();
  }

  /**
   * Cleanup all tracked personas via API
   */
  async cleanup(apiClient: any): Promise<void> {
    const emails = Array.from(this.createdPersonas);
    
    for (const email of emails) {
      try {
        await apiClient.delete(`/api/users?email=${email}`);
      } catch (error) {
        console.warn(`Failed to cleanup persona: ${email}`, error);
      }
    }
    
    this.clear();
  }
}

/**
 * Random data generators for realistic test data
 */
export class TestDataGenerator {
  private static readonly FIRST_NAMES = [
    'Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank',
    'Grace', 'Henry', 'Iris', 'Jack', 'Kate', 'Leo'
  ];

  private static readonly LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia',
    'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez'
  ];

  private static readonly COMPANIES = [
    'Acme Corp', 'TechStart Inc', 'Innovation Labs', 'Digital Solutions',
    'Cloud Systems', 'Secure Tech', 'DataFlow Inc', 'NextGen Solutions'
  ];

  static randomName(): string {
    const first = this.FIRST_NAMES[Math.floor(Math.random() * this.FIRST_NAMES.length)];
    const last = this.LAST_NAMES[Math.floor(Math.random() * this.LAST_NAMES.length)];
    return `${first} ${last}`;
  }

  static randomEmail(): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(7);
    return `test-${timestamp}-${random}@example.com`;
  }

  static randomCompany(): string {
    return this.COMPANIES[Math.floor(Math.random() * this.COMPANIES.length)];
  }

  static randomPassword(): string {
    // Generate secure random password
    const length = 16;
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*';
    let password = '';
    
    for (let i = 0; i < length; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    
    return password;
  }
}
