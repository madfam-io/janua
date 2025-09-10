import React from 'react'
import { render, screen } from '@testing-library/react'
import { button } from './button'

describe('button', () => {
  it('should render without crashing', () => {
    render(<button />)
    expect(screen.getByTestId('button')).toBeInTheDocument()
  })
})
