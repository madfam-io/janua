import React from 'react'
import { render } from '@testing-library/react'
import { ThemeProvider } from './theme-provider'

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

describe('ThemeProvider', () => {
  it('should render without crashing', () => {
    render(
      <ThemeProvider>
        <div data-testid="theme-provider">Test content</div>
      </ThemeProvider>
    )
  })
})
