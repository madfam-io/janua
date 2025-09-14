import React from 'react'
import { render, screen } from '@testing-library/react'
import RootLayout from './layout'

describe('RootLayout', () => {
  it('should render without crashing', () => {
    const TestChild = () => <div>Test Child</div>
    render(
      <RootLayout>
        <TestChild />
      </RootLayout>
    )
    expect(screen.getByText('Test Child')).toBeInTheDocument()
  })

  it('should render html and body tags', () => {
    const TestChild = () => <div>Content</div>
    const { container } = render(
      <RootLayout>
        <TestChild />
      </RootLayout>
    )
    expect(container.firstChild).toHaveProperty('tagName', 'HTML')
  })
})
