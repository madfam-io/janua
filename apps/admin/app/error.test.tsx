import React from 'react'
import { render, screen } from '@testing-library/react'
import { error } from './error'

describe('error', () => {
  it('should render without crashing', () => {
    render(<error />)
    expect(screen.getByTestId('error')).toBeInTheDocument()
  })
})
