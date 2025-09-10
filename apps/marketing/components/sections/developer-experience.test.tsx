import React from 'react'
import { render, screen } from '@testing-library/react'
import { developer-experience } from './developer-experience'

describe('developer-experience', () => {
  it('should render without crashing', () => {
    render(<developer-experience />)
    expect(screen.getByTestId('developer-experience')).toBeInTheDocument()
  })
})
