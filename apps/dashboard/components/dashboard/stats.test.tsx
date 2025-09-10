import React from 'react'
import { render, screen } from '@testing-library/react'
import { stats } from './stats'

describe('stats', () => {
  it('should render without crashing', () => {
    render(<stats />)
    expect(screen.getByTestId('stats')).toBeInTheDocument()
  })
})
