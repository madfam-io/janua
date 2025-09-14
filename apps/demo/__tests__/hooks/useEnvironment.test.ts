import { renderHook } from '@testing-library/react'
import { useEnvironment, useDemoFeatures, useApiConfig } from '@/hooks/useEnvironment'

// Mock the config module
jest.mock('@/lib/config', () => ({
  getEnvironment: jest.fn(() => ({
    name: 'demo',
    displayName: 'Demo',
    apiUrl: 'http://localhost:4000',
    wsUrl: 'ws://localhost:4000',
    publicUrl: 'http://localhost:3000',
    features: {
      sampleData: true,
      performanceMonitoring: true,
      debugMode: false,
      analytics: false
    }
  })),
  isDemo: jest.fn(() => true),
  isProduction: jest.fn(() => false),
  DEMO_CREDENTIALS: {
    email: 'demo@plinto.dev',
    password: 'DemoPassword123!'
  },
  DEMO_PERFORMANCE_METRICS: {
    edgeVerificationMs: 12,
    authFlowMs: 250,
    tokenGenerationMs: 45,
    globalLocations: 150
  }
}))

describe('useEnvironment', () => {
  it('should return environment configuration', () => {
    const { result } = renderHook(() => useEnvironment())
    
    expect(result.current.environment.name).toBe('demo')
    expect(result.current.environment.apiUrl).toBe('http://localhost:4000')
    expect(result.current.isDemo).toBe(true)
    expect(result.current.isProduction).toBe(false)
    expect(result.current.mounted).toBe(true)
  })
})

describe('useDemoFeatures', () => {
  it('should return demo features when in demo mode', () => {
    const { result } = renderHook(() => useDemoFeatures())

    expect(result.current.isDemo).toBe(true)
    expect(result.current.demoConfig).toBeDefined()
    expect(result.current.performanceData).toBeDefined()
    expect(result.current.generateSampleUsers).toBeDefined()
    expect(result.current.simulatePerformance).toBeDefined()
  })
})

describe('useApiConfig', () => {
  it('should return API configuration', () => {
    const { result } = renderHook(() => useApiConfig())

    expect(result.current).toEqual({
      apiUrl: 'http://localhost:4000',
      timeout: 2000, // Demo mode uses faster timeout
      retries: 1     // Demo mode uses fewer retries
    })
  })
})
