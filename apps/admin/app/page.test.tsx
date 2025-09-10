import React from 'react'
import { render, screen } from '@testing-library/react'
import { page } from './page'

describe('page', () => {
  it('should render without crashing', () => {
    render(<page />)
    expect(screen.getByTestId('page')).toBeInTheDocument()
  })
})
