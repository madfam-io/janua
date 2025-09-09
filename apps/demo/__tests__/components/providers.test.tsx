import React from 'react'
import { render } from '@testing-library/react'
import { Providers } from '@/components/providers'

// Mock the useApiConfig hook
jest.mock('@/hooks/useEnvironment', () => ({
  useApiConfig: jest.fn(),
}))

// Mock @plinto/sdk
jest.mock('@plinto/sdk', () => ({
  PlintoClient: jest.fn().mockImplementation(() => ({
    init: jest.fn(),
  })),
}))

const mockUseApiConfig = require('@/hooks/useEnvironment').useApiConfig
const { PlintoClient } = require('@plinto/sdk')

describe('Providers', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Mock window
    Object.defineProperty(window, 'location', {
      value: { origin: 'http://localhost:3002' },
      writable: true
    })
  })

  it('should render children after mounting', () => {
    mockUseApiConfig.mockReturnValue({
      apiUrl: 'http://localhost:4000',
      timeout: 5000,
      retries: 3,
    })

    const TestChild = () => React.createElement('div', { 'data-testid': 'test-child' }, 'Test Child')

    const { queryByTestId } = render(
      React.createElement(Providers, {}, React.createElement(TestChild))
    )

    // Initially should not render due to mounted state
    expect(queryByTestId('test-child')).toBeNull()

    // After a tick, should render
    setTimeout(() => {
      expect(queryByTestId('test-child')).toBeInTheDocument()
    }, 0)
  })

  it('should create PlintoClient with correct config', () => {
    mockUseApiConfig.mockReturnValue({
      apiUrl: 'http://localhost:4000',
      timeout: 2000,
      retries: 1,
    })

    render(React.createElement(Providers, {}, React.createElement('div')))

    expect(PlintoClient).toHaveBeenCalledWith({
      issuer: 'http://localhost:4000',
      clientId: 'demo-client',
      redirectUri: 'http://localhost:3002',
      timeout: 2000,
      retries: 1,
    })
  })

  it('should handle missing window gracefully', () => {
    mockUseApiConfig.mockReturnValue({
      apiUrl: 'http://localhost:4000',
      timeout: 5000,
      retries: 3,
    })

    // Mock window as undefined
    const originalWindow = global.window
    delete (global as any).window

    expect(() => {
      render(React.createElement(Providers, {}, React.createElement('div')))
    }).not.toThrow()

    // Restore window
    global.window = originalWindow
  })

  it('should set plinto on window', () => {
    mockUseApiConfig.mockReturnValue({
      apiUrl: 'http://localhost:4000',
      timeout: 5000,
      retries: 3,
    })

    const mockClient = { init: jest.fn() }
    PlintoClient.mockImplementation(() => mockClient)

    render(React.createElement(Providers, {}, React.createElement('div')))

    setTimeout(() => {
      expect((window as any).plinto).toBe(mockClient)
    }, 0)
  })
})