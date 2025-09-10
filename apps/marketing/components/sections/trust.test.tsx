import React from 'react'
import { render, screen } from '@testing-library/react'
import { trust } from './trust'

describe('trust', () => {
  it('should render without crashing', () => {
    render(<trust />)
    expect(screen.getByTestId('trust')).toBeInTheDocument()
  })
})
