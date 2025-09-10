import React from 'react'
import { render, screen } from '@testing-library/react'
import { label } from './label'

describe('label', () => {
  it('should render without crashing', () => {
    render(<label />)
    expect(screen.getByTestId('label')).toBeInTheDocument()
  })
})
