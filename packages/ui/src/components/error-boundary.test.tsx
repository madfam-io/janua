import React from 'react'
import { render, screen } from '@testing-library/react'
import { error-boundary } from './error-boundary'

describe('error-boundary', () => {
  it('should render without crashing', () => {
    render(<error-boundary />)
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument()
  })
})
