import {
  getEnvironment,
  isDemo,
  isProduction,
  getFeature,
  DEMO_CREDENTIALS,
  DEMO_PERFORMANCE_METRICS
} from '@/lib/config'

// Mock process.env
const originalEnv = process.env

beforeEach(() => {
  jest.resetModules()
  process.env = { ...originalEnv }
})

afterEach(() => {
  process.env = originalEnv
})

describe('config', () => {
  describe('getEnvironment', () => {
    it('should return demo environment when NEXT_PUBLIC_PLINTO_ENV is demo', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      
      const env = getEnvironment()
      
      expect(env.name).toBe('demo')
      expect(env.features.realSignups).toBe(false)
      expect(env.features.showDemoNotice).toBe(true)
      expect(env.features.autoSignIn).toBe(true)
      expect(env.demo).toBeDefined()
      expect(env.demo?.resetInterval).toBe(24)
    })

    it('should return staging environment when NEXT_PUBLIC_PLINTO_ENV is staging', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'staging'
      
      const env = getEnvironment()
      
      expect(env.name).toBe('staging')
      expect(env.features.realSignups).toBe(true)
      expect(env.features.realBilling).toBe(false)
      expect(env.features.showDemoNotice).toBe(false)
      expect(env.demo).toBeUndefined()
    })

    it('should return production environment when NEXT_PUBLIC_PLINTO_ENV is production', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'production'
      
      const env = getEnvironment()
      
      expect(env.name).toBe('production')
      expect(env.features.realSignups).toBe(true)
      expect(env.features.realBilling).toBe(true)
      expect(env.features.realEmails).toBe(true)
      expect(env.features.showDemoNotice).toBe(false)
      expect(env.demo).toBeUndefined()
    })

    it('should default to production when NEXT_PUBLIC_PLINTO_ENV is not set', () => {
      delete process.env.NEXT_PUBLIC_PLINTO_ENV
      
      const env = getEnvironment()
      
      expect(env.name).toBe('production')
    })

    it('should fallback to production for unknown environment', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'unknown'
      
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation(() => {})
      
      const env = getEnvironment()
      
      expect(env.name).toBe('production')
      expect(consoleSpy).toHaveBeenCalledWith('Unknown environment: unknown, falling back to production')
      
      consoleSpy.mockRestore()
    })

    it('should use environment-specific API URLs', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      process.env.NEXT_PUBLIC_DEMO_API_URL = 'https://demo-api.example.com'
      
      const env = getEnvironment()
      
      expect(env.apiUrl).toBe('https://demo-api.example.com')
    })

    it('should use default API URLs when env vars are not set', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      delete process.env.NEXT_PUBLIC_DEMO_API_URL
      
      const env = getEnvironment()
      
      expect(env.apiUrl).toBe('http://localhost:4000')
    })
  })

  describe('isDemo', () => {
    it('should return true when environment is demo', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      expect(isDemo()).toBe(true)
    })

    it('should return false when environment is not demo', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'production'
      expect(isDemo()).toBe(false)
    })
  })

  describe('isProduction', () => {
    it('should return true when environment is production', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'production'
      expect(isProduction()).toBe(true)
    })

    it('should return false when environment is not production', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      expect(isProduction()).toBe(false)
    })
  })

  describe('getFeature', () => {
    it('should return feature flag value for demo environment', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      
      expect(getFeature('realSignups')).toBe(false)
      expect(getFeature('showDemoNotice')).toBe(true)
      expect(getFeature('autoSignIn')).toBe(true)
    })

    it('should return feature flag value for production environment', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'production'
      
      expect(getFeature('realSignups')).toBe(true)
      expect(getFeature('showDemoNotice')).toBe(false)
      expect(getFeature('autoSignIn')).toBe(false)
    })

    it('should handle all feature flags', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'staging'
      
      expect(getFeature('realSignups')).toBe(true)
      expect(getFeature('realBilling')).toBe(false)
      expect(getFeature('realEmails')).toBe(false)
      expect(getFeature('dataRetention')).toBe(true)
      expect(getFeature('showDemoNotice')).toBe(false)
      expect(getFeature('autoSignIn')).toBe(false)
      expect(getFeature('demoCredentials')).toBe(false)
    })
  })

  describe('DEMO_CREDENTIALS', () => {
    it('should have required demo credentials', () => {
      expect(DEMO_CREDENTIALS).toEqual({
        email: 'demo@plinto.dev',
        password: 'DemoPassword123!',
        name: 'Demo User'
      })
    })

    it('should have valid email format', () => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      expect(emailRegex.test(DEMO_CREDENTIALS.email)).toBe(true)
    })

    it('should have non-empty password', () => {
      expect(DEMO_CREDENTIALS.password).toBeTruthy()
      expect(DEMO_CREDENTIALS.password.length).toBeGreaterThan(0)
    })
  })

  describe('DEMO_PERFORMANCE_METRICS', () => {
    it('should have valid performance metrics', () => {
      expect(DEMO_PERFORMANCE_METRICS).toEqual({
        edgeVerificationMs: 12,
        tokenGenerationMs: 45,
        authFlowMs: 230,
        globalLocations: 150
      })
    })

    it('should have positive numeric values', () => {
      Object.values(DEMO_PERFORMANCE_METRICS).forEach(value => {
        expect(typeof value).toBe('number')
        expect(value).toBeGreaterThan(0)
      })
    })

    it('should have realistic performance values', () => {
      expect(DEMO_PERFORMANCE_METRICS.edgeVerificationMs).toBeLessThan(100)
      expect(DEMO_PERFORMANCE_METRICS.tokenGenerationMs).toBeLessThan(1000)
      expect(DEMO_PERFORMANCE_METRICS.authFlowMs).toBeLessThan(5000)
      expect(DEMO_PERFORMANCE_METRICS.globalLocations).toBeGreaterThan(1)
    })
  })

  describe('Environment interface compliance', () => {
    it('should have all required properties in demo environment', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      
      const env = getEnvironment()
      
      expect(env).toHaveProperty('name')
      expect(env).toHaveProperty('apiUrl')
      expect(env).toHaveProperty('appUrl')
      expect(env).toHaveProperty('features')
      expect(env).toHaveProperty('demo')
      
      expect(env.features).toHaveProperty('realSignups')
      expect(env.features).toHaveProperty('realBilling')
      expect(env.features).toHaveProperty('realEmails')
      expect(env.features).toHaveProperty('dataRetention')
      expect(env.features).toHaveProperty('showDemoNotice')
      expect(env.features).toHaveProperty('autoSignIn')
      expect(env.features).toHaveProperty('demoCredentials')
      
      expect(env.demo).toHaveProperty('resetInterval')
      expect(env.demo).toHaveProperty('sampleDataEnabled')
      expect(env.demo).toHaveProperty('performanceSimulation')
      expect(env.demo).toHaveProperty('interactiveTutorial')
    })

    it('should have all required properties in production environment', () => {
      process.env.NEXT_PUBLIC_PLINTO_ENV = 'production'
      
      const env = getEnvironment()
      
      expect(env).toHaveProperty('name')
      expect(env).toHaveProperty('apiUrl')
      expect(env).toHaveProperty('appUrl')
      expect(env).toHaveProperty('features')
      expect(env.demo).toBeUndefined()
    })
  })
})