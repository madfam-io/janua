import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import Error from './error'

// Mock console.error to avoid cluttering test output
const originalConsoleError = console.error
beforeEach(() => {
  console.error = jest.fn()
})

afterEach(() => {
  console.error = originalConsoleError
})

describe('Error', () => {
  const mockReset = jest.fn()
  const mockError = new Error('Test error')

  beforeEach(() => {
    mockReset.mockClear()
  })

  it('should render general error message', () => {
    render(<Error error={mockError} reset={mockReset} />)
    
    expect(screen.getByText('Documentation Error')).toBeInTheDocument()
    expect(screen.getByText('We encountered an error while loading the documentation.')).toBeInTheDocument()
  })

  it('should render 404 error when error message contains "404"', () => {
    const notFoundError = new Error('404 - Not found')
    render(<Error error={notFoundError} reset={mockReset} />)
    
    expect(screen.getByText('Documentation Not Found')).toBeInTheDocument()
    expect(screen.getByText(/The documentation page you're looking for doesn't exist/)).toBeInTheDocument()
  })

  it('should render search error when error message contains "search"', () => {
    const searchError = new Error('Search failed')
    render(<Error error={searchError} reset={mockReset} />)
    
    expect(screen.getByText('Search Error')).toBeInTheDocument()
    expect(screen.getByText('We encountered an error while searching the documentation.')).toBeInTheDocument()
  })

  it('should call reset function when "Try Again" is clicked', () => {
    render(<Error error={mockError} reset={mockReset} />)
    
    const tryAgainButton = screen.getByText('Try Again')
    fireEvent.click(tryAgainButton)
    
    expect(mockReset).toHaveBeenCalledTimes(1)
  })

  it('should show 404 specific links and buttons', () => {
    const notFoundError = new Error('404 - Not found')
    render(<Error error={notFoundError} reset={mockReset} />)
    
    expect(screen.getByText('📚 Documentation Home')).toBeInTheDocument()
    expect(screen.getByText('🚀 Getting Started Guide')).toBeInTheDocument()
    expect(screen.getByText('📖 API Reference')).toBeInTheDocument()
    expect(screen.getByText('Documentation Home')).toBeInTheDocument()
    expect(screen.getByText('Search Docs')).toBeInTheDocument()
  })

  it('should log error to console', () => {
    render(<Error error={mockError} reset={mockReset} />)
    
    expect(console.error).toHaveBeenCalledWith('Documentation error:', mockError)
  })
})