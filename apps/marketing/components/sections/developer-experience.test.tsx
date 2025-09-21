import React from 'react'
import { render, screen } from '@testing-library/react'
import { DeveloperExperience } from './developer-experience'

describe('DeveloperExperience', () => {
  it('should render without crashing', () => {
    render(<DeveloperExperience />)
    expect(screen.getByText('Ship authentication in minutes, not days')).toBeInTheDocument()
  })
})