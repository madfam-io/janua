import React from 'react'
import { render, screen } from '@testing-library/react'
import { dialog } from './dialog'

describe('dialog', () => {
  it('should render without crashing', () => {
    render(<dialog />)
    expect(screen.getByTestId('dialog')).toBeInTheDocument()
  })
})
