import React from 'react'
import { render, screen } from '@testing-library/react'
import { cta } from './cta'

describe('cta', () => {
  it('should render without crashing', () => {
    render(<cta />)
    expect(screen.getByTestId('cta')).toBeInTheDocument()
  })
})
