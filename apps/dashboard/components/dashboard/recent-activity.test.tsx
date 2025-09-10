import React from 'react'
import { render, screen } from '@testing-library/react'
import { recent-activity } from './recent-activity'

describe('recent-activity', () => {
  it('should render without crashing', () => {
    render(<recent-activity />)
    expect(screen.getByTestId('recent-activity')).toBeInTheDocument()
  })
})
