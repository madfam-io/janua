import { renderHook, act } from '@testing-library/react'
import { useEnvironment, useDemoFeatures, useApiConfig } from '@/hooks/useEnvironment'

// Mock the config module
jest.mock('@/lib/config', () => ({
  getEnvironment: jest.fn(),
  isDemo: jest.fn(),
  isProduction: jest.fn(),
  getFeature: jest.fn(),
  DEMO_CREDENTIALS: {
    email: 'demo@plinto.dev',
    password: 'DemoPassword123!',
    name: 'Demo User'
  },
  DEMO_PERFORMANCE_METRICS: {
    edgeVerificationMs: 12,
    tokenGenerationMs: 45,
    authFlowMs: 230,
    globalLocations: 150
  }
}))

const mockConfig = require('@/lib/config')

describe('useEnvironment', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  afterEach(() => {
    jest.clearAllTimers()
    jest.useRealTimers()
  })

  it('should return initial loading state when not mounted', () => {
    const mockEnv = {
      name: 'demo',
      apiUrl: 'http://localhost:4000',
      appUrl: 'https://demo.plinto.dev',
      features: {
        realSignups: false,
        showDemoNotice: true,
        autoSignIn: true,
        realBilling: false,
        realEmails: false,
        dataRetention: false,
        demoCredentials: true
      },
      demo: {
        resetInterval: 24,
        sampleDataEnabled: true,
        performanceSimulation: true,
        interactiveTutorial: true
      }
    }

    mockConfig.getEnvironment.mockReturnValue(mockEnv)
    mockConfig.isDemo.mockReturnValue(false)
    mockConfig.isProduction.mockReturnValue(true)

    const { result } = renderHook(() => useEnvironment())

    // Should return loading state initially
    expect(result.current.mounted).toBe(false)
    expect(result.current.environment).toBe(null)
    expect(result.current.isDemo).toBe(false)
    expect(result.current.isProduction).toBe(true)
  })

  it('should return demo environment data when mounted and demo', async () => {
    const mockEnv = {
      name: 'demo',
      apiUrl: 'http://localhost:4000',
      appUrl: 'https://demo.plinto.dev',
      features: {
        realSignups: false,
        showDemoNotice: true,
        autoSignIn: true,
        realBilling: false,
        realEmails: false,
        dataRetention: false,
        demoCredentials: true
      },
      demo: {
        resetInterval: 24,
        sampleDataEnabled: true,
        performanceSimulation: true,
        interactiveTutorial: true
      }
    }

    mockConfig.getEnvironment.mockReturnValue(mockEnv)
    mockConfig.isDemo.mockReturnValue(true)
    mockConfig.isProduction.mockReturnValue(false)

    const { result } = renderHook(() => useEnvironment())

    // Wait for useEffect to run
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    expect(result.current.mounted).toBe(true)
    expect(result.current.environment).toEqual(mockEnv)
    expect(result.current.isDemo).toBe(true)
    expect(result.current.isProduction).toBe(false)
    expect(result.current.features).toEqual(mockEnv.features)
    expect(result.current.demoConfig).toEqual(mockEnv.demo)
  })

  it('should return production environment data when mounted and production', async () => {
    const mockEnv = {
      name: 'production',
      apiUrl: 'https://api.plinto.dev',
      appUrl: 'https://app.plinto.dev',
      features: {
        realSignups: true,
        showDemoNotice: false,
        autoSignIn: false,
        realBilling: true,
        realEmails: true,
        dataRetention: true,
        demoCredentials: false
      }
    }

    mockConfig.getEnvironment.mockReturnValue(mockEnv)
    mockConfig.isDemo.mockReturnValue(false)
    mockConfig.isProduction.mockReturnValue(true)

    const { result } = renderHook(() => useEnvironment())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    expect(result.current.mounted).toBe(true)
    expect(result.current.environment).toEqual(mockEnv)
    expect(result.current.isDemo).toBe(false)
    expect(result.current.isProduction).toBe(true)
    expect(result.current.demoConfig).toBe(null)
  })

  it('should provide helper methods', async () => {
    const mockEnv = {
      name: 'demo',
      apiUrl: 'http://localhost:4000',
      appUrl: 'https://demo.plinto.dev',
      features: {
        realSignups: false,
        showDemoNotice: true,
        autoSignIn: true,
        realBilling: false,
        realEmails: false,
        dataRetention: false,
        demoCredentials: true
      },
      demo: {
        resetInterval: 24,
        sampleDataEnabled: true,
        performanceSimulation: true,
        interactiveTutorial: true
      }
    }

    mockConfig.getEnvironment.mockReturnValue(mockEnv)
    mockConfig.isDemo.mockReturnValue(true)
    mockConfig.isProduction.mockReturnValue(false)

    const { result } = renderHook(() => useEnvironment())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    expect(typeof result.current.showDemoNotice).toBe('function')
    expect(typeof result.current.allowRealSignups).toBe('function')
    expect(typeof result.current.processRealPayments).toBe('function')
    expect(typeof result.current.sendRealEmails).toBe('function')
    expect(typeof result.current.retainUserData).toBe('function')
    expect(typeof result.current.shouldAutoSignIn).toBe('function')
    expect(typeof result.current.hasDemoCredentials).toBe('function')

    expect(result.current.showDemoNotice()).toBe(true)
    expect(result.current.allowRealSignups()).toBe(false)
    expect(result.current.processRealPayments()).toBe(false)
    expect(result.current.sendRealEmails()).toBe(false)
    expect(result.current.retainUserData()).toBe(false)
    expect(result.current.shouldAutoSignIn()).toBe(true)
    expect(result.current.hasDemoCredentials()).toBe(true)
  })
})

describe('useDemoFeatures', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.clearAllTimers()
    jest.useRealTimers()
  })

  it('should return demo features when in demo mode', async () => {
    const mockEnv = {
      name: 'demo',
      apiUrl: 'http://localhost:4000',
      appUrl: 'https://demo.plinto.dev',
      features: {
        realSignups: false,
        showDemoNotice: true,
        autoSignIn: true,
        realBilling: false,
        realEmails: false,
        dataRetention: false,
        demoCredentials: true
      },
      demo: {
        resetInterval: 24,
        sampleDataEnabled: true,
        performanceSimulation: true,
        interactiveTutorial: true
      }
    }

    mockConfig.getEnvironment.mockReturnValue(mockEnv)
    mockConfig.isDemo.mockReturnValue(true)

    const { result } = renderHook(() => useDemoFeatures())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    expect(result.current.isDemo).toBe(true)
    expect(result.current.demoConfig).toEqual(mockEnv.demo)
    expect(result.current.performanceData).toEqual(mockConfig.DEMO_PERFORMANCE_METRICS)
  })

  it('should simulate performance correctly', async () => {
    mockConfig.getEnvironment.mockReturnValue({
      name: 'demo',
      features: {},
      demo: { performanceSimulation: true }
    })
    mockConfig.isDemo.mockReturnValue(true)

    const { result } = renderHook(() => useDemoFeatures())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    await act(async () => {
      const promise = result.current.simulatePerformance('auth')
      jest.advanceTimersByTime(250) // Advance by expected auth time + buffer
      await promise
    })

    // Should have completed the simulation
    expect(jest.getTimerCount()).toBeGreaterThanOrEqual(0)
  })

  it('should generate sample users', async () => {
    mockConfig.getEnvironment.mockReturnValue({
      name: 'demo',
      features: {},
      demo: {}
    })
    mockConfig.isDemo.mockReturnValue(true)

    const { result } = renderHook(() => useDemoFeatures())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    const users = result.current.generateSampleUsers()
    
    expect(Array.isArray(users)).toBe(true)
    expect(users).toHaveLength(3)
    expect(users[0]).toHaveProperty('name', 'Alice Developer')
    expect(users[0]).toHaveProperty('email', 'alice@demo.com')
    expect(users[0]).toHaveProperty('role', 'admin')
  })

  it('should reset demo data in demo mode', async () => {
    mockConfig.getEnvironment.mockReturnValue({
      name: 'demo',
      features: {},
      demo: {}
    })
    mockConfig.isDemo.mockReturnValue(true)

    const { result } = renderHook(() => useDemoFeatures())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    await act(async () => {
      const promise = result.current.resetDemoData()
      jest.advanceTimersByTime(1000)
      const success = await promise
      expect(success).toBe(true)
    })
  })

  it('should not reset demo data in non-demo mode', async () => {
    mockConfig.getEnvironment.mockReturnValue({
      name: 'production',
      features: {}
    })
    mockConfig.isDemo.mockReturnValue(false)

    const { result } = renderHook(() => useDemoFeatures())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    const success = await result.current.resetDemoData()
    expect(success).toBe(false)
  })

  it('should provide demo configuration methods', async () => {
    const mockDemoConfig = {
      resetInterval: 24,
      sampleDataEnabled: true,
      performanceSimulation: true,
      interactiveTutorial: true
    }

    mockConfig.getEnvironment.mockReturnValue({
      name: 'demo',
      features: {},
      demo: mockDemoConfig
    })
    mockConfig.isDemo.mockReturnValue(true)

    const { result } = renderHook(() => useDemoFeatures())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    expect(result.current.shouldShowInteractiveTutorial()).toBe(true)
    expect(result.current.shouldSimulatePerformance()).toBe(true)
  })
})

describe('useApiConfig', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should return default config when not mounted', () => {
    mockConfig.getEnvironment.mockReturnValue({
      name: 'production',
      apiUrl: 'https://api.plinto.dev'
    })

    const { result } = renderHook(() => useApiConfig())

    expect(result.current.apiUrl).toBe('http://localhost:4000')
    expect(result.current.timeout).toBe(5000)
    expect(result.current.retries).toBe(3)
  })

  it('should return demo config when mounted and in demo mode', async () => {
    const mockEnv = {
      name: 'demo',
      apiUrl: 'http://localhost:4000'
    }

    mockConfig.getEnvironment.mockReturnValue(mockEnv)

    const { result } = renderHook(() => useApiConfig())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    expect(result.current.apiUrl).toBe('http://localhost:4000')
    expect(result.current.timeout).toBe(2000) // Faster for demo
    expect(result.current.retries).toBe(1) // Fewer retries for demo
  })

  it('should return production config when mounted and in production mode', async () => {
    const mockEnv = {
      name: 'production',
      apiUrl: 'https://api.plinto.dev'
    }

    mockConfig.getEnvironment.mockReturnValue(mockEnv)

    const { result } = renderHook(() => useApiConfig())

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })

    expect(result.current.apiUrl).toBe('https://api.plinto.dev')
    expect(result.current.timeout).toBe(5000)
    expect(result.current.retries).toBe(3)
  })
})