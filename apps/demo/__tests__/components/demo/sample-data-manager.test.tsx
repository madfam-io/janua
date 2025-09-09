import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { SampleDataManager } from '@/components/demo/sample-data-manager'

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: (props) => React.createElement('div', props, props.children),
  },
}))

// Mock the useDemoFeatures hook
jest.mock('@/hooks/useEnvironment', () => ({
  useDemoFeatures: jest.fn(),
}))

// Mock @plinto/ui components
jest.mock('@plinto/ui', () => ({
  Button: (props) => React.createElement('button', props, props.children),
  Card: (props) => React.createElement('div', { 'data-testid': 'card', ...props }, props.children),
  CardContent: (props) => React.createElement('div', { 'data-testid': 'card-content', ...props }, props.children),
  CardDescription: (props) => React.createElement('div', { 'data-testid': 'card-description', ...props }, props.children),
  CardHeader: (props) => React.createElement('div', { 'data-testid': 'card-header', ...props }, props.children),
  CardTitle: (props) => React.createElement('div', { 'data-testid': 'card-title', ...props }, props.children),
}))

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Users: (props) => React.createElement('span', { 'data-testid': 'users-icon', ...props }),
  RefreshCw: (props) => React.createElement('span', { 'data-testid': 'refresh-cw-icon', ...props }),
  Database: (props) => React.createElement('span', { 'data-testid': 'database-icon', ...props }),
  Plus: (props) => React.createElement('span', { 'data-testid': 'plus-icon', ...props }),
}))

const mockUseDemoFeatures = require('@/hooks/useEnvironment').useDemoFeatures

describe('SampleDataManager', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it('should not render when not in demo mode', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: false,
      generateSampleUsers: jest.fn(),
    })

    const { container } = render(<SampleDataManager />)
    expect(container.firstChild).toBeNull()
  })

  it('should render sample data manager when in demo mode', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      generateSampleUsers: jest.fn(() => []),
    })

    render(<SampleDataManager />)

    expect(screen.getByTestId('database-icon')).toBeInTheDocument()
    expect(screen.getByText('Sample Data Manager')).toBeInTheDocument()
    expect(screen.getByText('Generate and manage sample users for demonstration')).toBeInTheDocument()
    expect(screen.getByText('Generate Users')).toBeInTheDocument()
    expect(screen.getByTestId('plus-icon')).toBeInTheDocument()
  })

  it('should generate sample users when Generate Users button is clicked', async () => {
    const mockGenerateUsers = jest.fn(() => [
      { id: '1', name: 'Alice Developer', email: 'alice@demo.com', role: 'admin' },
      { id: '2', name: 'Bob Designer', email: 'bob@demo.com', role: 'member' },
    ])

    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      generateSampleUsers: mockGenerateUsers,
    })

    render(<SampleDataManager />)

    const generateButton = screen.getByText('Generate Users')
    fireEvent.click(generateButton)

    // Should show loading state
    expect(screen.getByText('Loading...')).toBeInTheDocument()
    expect(screen.getByTestId('refresh-cw-icon')).toBeInTheDocument()
    expect(generateButton).toBeDisabled()

    // Fast-forward time
    jest.advanceTimersByTime(800)

    await waitFor(() => {
      expect(screen.getByText('Sample Users (2)')).toBeInTheDocument()
      expect(screen.getByText('Alice Developer')).toBeInTheDocument()
      expect(screen.getByText('alice@demo.com')).toBeInTheDocument()
      expect(screen.getByText('Bob Designer')).toBeInTheDocument()
      expect(screen.getByText('bob@demo.com')).toBeInTheDocument()
    })

    expect(mockGenerateUsers).toHaveBeenCalled()
  })

  it('should add random user when plus button is clicked', async () => {
    const mockGenerateUsers = jest.fn(() => [
      { id: '1', name: 'Alice Developer', email: 'alice@demo.com', role: 'admin' },
    ])

    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      generateSampleUsers: mockGenerateUsers,
    })

    render(<SampleDataManager />)

    // First generate users
    const generateButton = screen.getByText('Generate Users')
    fireEvent.click(generateButton)
    jest.advanceTimersByTime(800)

    await waitFor(() => {
      expect(screen.getByText('Sample Users (1)')).toBeInTheDocument()
    })

    // Then add random user
    const addButton = screen.getByTestId('plus-icon').closest('button')
    fireEvent.click(addButton)

    await waitFor(() => {
      expect(screen.getByText('Sample Users (2)')).toBeInTheDocument()
      // Should have one of the random names
      const hasRandomUser = ['David Engineer', 'Eva Manager', 'Frank Developer', 'Grace Analyst']
        .some(name => screen.queryByText(name))
      expect(hasRandomUser).toBe(true)
    })
  })

  it('should disable add button when no sample users exist', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      generateSampleUsers: jest.fn(() => []),
    })

    render(<SampleDataManager />)

    const addButton = screen.getByTestId('plus-icon').closest('button')
    expect(addButton).toBeDisabled()
  })

  it('should enable add button after generating users', async () => {
    const mockGenerateUsers = jest.fn(() => [
      { id: '1', name: 'Alice Developer', email: 'alice@demo.com', role: 'admin' },
    ])

    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      generateSampleUsers: mockGenerateUsers,
    })

    render(<SampleDataManager />)

    const addButton = screen.getByTestId('plus-icon').closest('button')
    expect(addButton).toBeDisabled()

    const generateButton = screen.getByText('Generate Users')
    fireEvent.click(generateButton)
    jest.advanceTimersByTime(800)

    await waitFor(() => {
      expect(addButton).not.toBeDisabled()
    })
  })

  it('should display demo disclaimer', () => {
    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      generateSampleUsers: jest.fn(() => []),
    })

    render(<SampleDataManager />)

    expect(screen.getByText('Demo Feature:')).toBeInTheDocument()
    expect(screen.getByText(/Generated users are for demonstration only/)).toBeInTheDocument()
    expect(screen.getByText(/In production, user data is securely stored/)).toBeInTheDocument()
  })

  it('should handle loading state correctly', async () => {
    const mockGenerateUsers = jest.fn(() => [])

    mockUseDemoFeatures.mockReturnValue({
      isDemo: true,
      generateSampleUsers: mockGenerateUsers,
    })

    render(<SampleDataManager />)

    const generateButton = screen.getByText('Generate Users')
    
    // Initially should not be loading
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    expect(screen.getByTestId('users-icon')).toBeInTheDocument()
    expect(generateButton).not.toBeDisabled()

    // Click generate
    fireEvent.click(generateButton)

    // Should be loading
    expect(screen.getByText('Loading...')).toBeInTheDocument()
    expect(screen.getByTestId('refresh-cw-icon')).toBeInTheDocument()
    expect(generateButton).toBeDisabled()

    // After timeout, should not be loading
    jest.advanceTimersByTime(800)

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      expect(screen.getByTestId('users-icon')).toBeInTheDocument()
      expect(generateButton).not.toBeDisabled()
    })
  })
})