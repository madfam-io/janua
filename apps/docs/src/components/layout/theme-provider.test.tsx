import React from 'react'
import { render, screen } from '@testing-library/react'
import { theme-provider } from './theme-provider'

describe('theme-provider', () => {
  it('should render without crashing', () => {
    render(<theme-provider />)
    expect(screen.getByTestId('theme-provider')).toBeInTheDocument()
  })
})
