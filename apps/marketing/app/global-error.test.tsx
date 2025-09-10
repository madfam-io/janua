import React from 'react'
import { render, screen } from '@testing-library/react'
import { global-error } from './global-error'

describe('global-error', () => {
  it('should render without crashing', () => {
    render(<global-error />)
    expect(screen.getByTestId('global-error')).toBeInTheDocument()
  })
})
