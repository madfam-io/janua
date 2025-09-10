import React from 'react'
import { render, screen } from '@testing-library/react'
import { toast } from './toast'

describe('toast', () => {
  it('should render without crashing', () => {
    render(<toast />)
    expect(screen.getByTestId('toast')).toBeInTheDocument()
  })
})
