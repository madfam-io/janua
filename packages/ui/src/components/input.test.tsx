import React from 'react'
import { render, screen } from '@testing-library/react'
import { input } from './input'

describe('input', () => {
  it('should render without crashing', () => {
    render(<input />)
    expect(screen.getByTestId('input')).toBeInTheDocument()
  })
})
