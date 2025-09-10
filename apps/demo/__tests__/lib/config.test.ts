/**
 * @jest-environment jsdom
 */

import { getEnvironment, isDemo, isProduction, getFeature, DEMO_CREDENTIALS, DEMO_PERFORMANCE_METRICS } from '@/lib/config'

// Mock Next.js environment variables
const mockEnv = {
  NEXT_PUBLIC_PLINTO_ENV: 'demo',
  NEXT_PUBLIC_API_URL: '',
  NEXT_PUBLIC_APP_URL: ''
}

// Mock process.env
Object.defineProperty(process, 'env', {
  value: mockEnv,
  writable: true
})

describe('config', () => {
  beforeEach(() => {
    // Reset environment variables
    mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'demo'
    mockEnv.NEXT_PUBLIC_API_URL = ''
    mockEnv.NEXT_PUBLIC_APP_URL = ''
  })

  describe('getEnvironment', () => {
    it('should return demo environment when NEXT_PUBLIC_PLINTO_ENV is demo', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      const env = getEnvironment()
      
      expect(env.name).toBe('demo')
      expect(env.apiUrl).toBe('http://localhost:4000')
      expect(env.features.showDemoNotice).toBe(true)
      expect(env.features.realSignups).toBe(false)
      expect(env.demo).toBeDefined()
    })

    it('should return staging environment when NEXT_PUBLIC_PLINTO_ENV is staging', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'staging'
      const env = getEnvironment()
      
      expect(env.name).toBe('staging')
      expect(env.apiUrl).toBe('https://staging-api.plinto.dev')
      expect(env.features.showDemoNotice).toBe(false)
      expect(env.features.realSignups).toBe(true)
    })

    it('should return production environment when NEXT_PUBLIC_PLINTO_ENV is production', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'production'
      const env = getEnvironment()
      
      expect(env.name).toBe('production')
      expect(env.apiUrl).toBe('https://api.plinto.dev')
      expect(env.features.realSignups).toBe(true)
      expect(env.features.realBilling).toBe(true)
    })

    it('should default to production when NEXT_PUBLIC_PLINTO_ENV is not set', () => {
      delete mockEnv.NEXT_PUBLIC_PLINTO_ENV
      const env = getEnvironment()
      
      expect(env.name).toBe('production')
      expect(env.apiUrl).toBe('https://api.plinto.dev')
    })

    it('should fallback to production for unknown environment', () => {
      // This should trigger the console.warn and fallback
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation()
      
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'unknown'
      const env = getEnvironment()
      
      expect(env.name).toBe('production')
      expect(consoleSpy).toHaveBeenCalledWith('Unknown environment: unknown, falling back to production')
      
      consoleSpy.mockRestore()
    })

    it('should use environment-specific API URLs', () => {
      mockEnv.NEXT_PUBLIC_API_URL = 'https://custom-api.example.com'
      const env = getEnvironment()
      
      expect(env.apiUrl).toBe('https://custom-api.example.com')
    })

    it('should use default API URLs when env vars are not set', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'staging'
      delete mockEnv.NEXT_PUBLIC_API_URL
      
      const env = getEnvironment()
      expect(env.apiUrl).toBe('https://staging-api.plinto.dev')
    })
  })

  describe('isDemo', () => {
    it('should return true when environment is demo', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      expect(isDemo()).toBe(true)
    })

    it('should return false when environment is not demo', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'production'
      expect(isDemo()).toBe(false)
    })
  })

  describe('isProduction', () => {
    it('should return true when environment is production', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'production'
      expect(isProduction()).toBe(true)
    })

    it('should return false when environment is not production', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      expect(isProduction()).toBe(false)
    })
  })

  describe('getFeature', () => {
    it('should return feature flag value for demo environment', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      expect(getFeature('showDemoNotice')).toBe(true)
      expect(getFeature('realSignups')).toBe(false)
    })

    it('should return feature flag value for production environment', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'production'
      expect(getFeature('showDemoNotice')).toBe(false)
      expect(getFeature('realSignups')).toBe(true)
      expect(getFeature('realBilling')).toBe(true)
    })

    it('should handle all feature flags', () => {
      const features = [
        'showDemoNotice',
        'realSignups', 
        'realBilling',
        'realEmails',
        'dataRetention',
        'autoSignIn',
        'demoCredentials'
      ]
      
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      
      features.forEach(feature => {
        const value = getFeature(feature as any)
        expect(typeof value).toBe('boolean')
      })
    })
  })

  describe('DEMO_CREDENTIALS', () => {
    it('should have required demo credentials', () => {
      expect(DEMO_CREDENTIALS).toBeDefined()
      expect(DEMO_CREDENTIALS.email).toBeDefined()
      expect(DEMO_CREDENTIALS.password).toBeDefined()
      expect(DEMO_CREDENTIALS.name).toBeDefined()
    })

    it('should have valid email format', () => {
      expect(DEMO_CREDENTIALS.email).toMatch(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)
    })

    it('should have non-empty password', () => {
      expect(DEMO_CREDENTIALS.password.length).toBeGreaterThan(0)
    })
  })

  describe('DEMO_PERFORMANCE_METRICS', () => {
    it('should have valid performance metrics', () => {
      expect(DEMO_PERFORMANCE_METRICS).toBeDefined()
      expect(DEMO_PERFORMANCE_METRICS.edgeVerificationMs).toBeDefined()
      expect(DEMO_PERFORMANCE_METRICS.tokenGenerationMs).toBeDefined()
      expect(DEMO_PERFORMANCE_METRICS.authFlowMs).toBeDefined()
      expect(DEMO_PERFORMANCE_METRICS.globalLocations).toBeDefined()
    })

    it('should have positive numeric values', () => {
      Object.values(DEMO_PERFORMANCE_METRICS).forEach(value => {
        expect(typeof value).toBe('number')
        expect(value).toBeGreaterThan(0)
      })
    })

    it('should have realistic performance values', () => {
      expect(DEMO_PERFORMANCE_METRICS.edgeVerificationMs).toBeLessThan(100)
      expect(DEMO_PERFORMANCE_METRICS.tokenGenerationMs).toBeLessThan(200)
      expect(DEMO_PERFORMANCE_METRICS.authFlowMs).toBeLessThan(1000)
      expect(DEMO_PERFORMANCE_METRICS.globalLocations).toBeGreaterThan(50)
    })
  })

  describe('Environment interface compliance', () => {
    it('should have all required properties in demo environment', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'demo'
      const env = getEnvironment()
      
      const requiredProps = ['name', 'apiUrl', 'appUrl', 'features']
      requiredProps.forEach(prop => {
        expect(env).toHaveProperty(prop)
      })
      
      // Demo should have demo config
      expect(env).toHaveProperty('demo')
    })

    it('should have all required properties in production environment', () => {
      mockEnv.NEXT_PUBLIC_PLINTO_ENV = 'production'
      const env = getEnvironment()
      
      const requiredProps = ['name', 'apiUrl', 'appUrl', 'features']
      requiredProps.forEach(prop => {
        expect(env).toHaveProperty(prop)
      })
      
      // Production should not have demo config
      expect(env.demo).toBeUndefined()
    })
  })
})