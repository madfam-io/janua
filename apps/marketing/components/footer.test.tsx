import React from 'react'
import { render, screen } from '@testing-library/react'
import { footer } from './footer'

describe('footer', () => {
  it('should render without crashing', () => {
    render(<footer />)
    expect(screen.getByTestId('footer')).toBeInTheDocument()
  })
})
