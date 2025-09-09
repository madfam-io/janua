export interface Environment {
  name: 'demo' | 'staging' | 'production'
  apiUrl: string
  appUrl: string
  features: {
    realSignups: boolean
    realBilling: boolean
    realEmails: boolean
    dataRetention: boolean
    showDemoNotice: boolean
    autoSignIn: boolean
    demoCredentials: boolean
  }
  demo?: {
    resetInterval: number // hours
    sampleDataEnabled: boolean
    performanceSimulation: boolean
    interactiveTutorial: boolean
  }
}

const environments: Record<string, Environment> = {
  demo: {
    name: 'demo',
    apiUrl: process.env.NEXT_PUBLIC_DEMO_API_URL || 'http://localhost:4000',
    appUrl: 'https://demo.plinto.dev',
    features: {
      realSignups: false,
      realBilling: false,
      realEmails: false,
      dataRetention: false,
      showDemoNotice: true,
      autoSignIn: true,
      demoCredentials: true,
    },
    demo: {
      resetInterval: 24, // Reset every 24 hours
      sampleDataEnabled: true,
      performanceSimulation: true,
      interactiveTutorial: true,
    }
  },
  staging: {
    name: 'staging',
    apiUrl: process.env.NEXT_PUBLIC_STAGING_API_URL || 'https://staging-api.plinto.dev',
    appUrl: 'https://staging.plinto.dev',
    features: {
      realSignups: true,
      realBilling: false,
      realEmails: false,
      dataRetention: true,
      showDemoNotice: false,
      autoSignIn: false,
      demoCredentials: false,
    }
  },
  production: {
    name: 'production',
    apiUrl: process.env.NEXT_PUBLIC_API_URL || 'https://api.plinto.dev',
    appUrl: 'https://app.plinto.dev',
    features: {
      realSignups: true,
      realBilling: true,
      realEmails: true,
      dataRetention: true,
      showDemoNotice: false,
      autoSignIn: false,
      demoCredentials: false,
    }
  }
}

export function getEnvironment(): Environment {
  const envName = process.env.NEXT_PUBLIC_PLINTO_ENV || 'production'
  const environment = environments[envName]
  
  if (!environment) {
    console.warn(`Unknown environment: ${envName}, falling back to production`)
    return environments.production
  }
  
  return environment
}

export function isDemo(): boolean {
  return getEnvironment().name === 'demo'
}

export function isProduction(): boolean {
  return getEnvironment().name === 'production'
}

export function getFeature(feature: keyof Environment['features']): boolean {
  return getEnvironment().features[feature]
}

// Demo-specific constants
export const DEMO_CREDENTIALS = {
  email: 'demo@plinto.dev',
  password: 'DemoPassword123!',
  name: 'Demo User'
}

export const DEMO_PERFORMANCE_METRICS = {
  edgeVerificationMs: 12,
  tokenGenerationMs: 45,
  authFlowMs: 230,
  globalLocations: 150
}