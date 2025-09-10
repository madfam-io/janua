import React from 'react'
import { render, screen } from '@testing-library/react'
import { tabs } from './tabs'

describe('tabs', () => {
  it('should render without crashing', () => {
    render(<tabs />)
    expect(screen.getByTestId('tabs')).toBeInTheDocument()
  })
})
