import React from 'react'
import { render, screen } from '@testing-library/react'
import { IdentityList } from './identity-list'

// TODO(janua-tests): STALE TEST. The component renders (a loading spinner at
// assert time), but asserts a data-testid="identity-list" it does not set.
// Scaffold stub, not real coverage. Needs a real assertion, awaited.
describe.skip('IdentityList', () => {
  it('should render without crashing', () => {
    render(<IdentityList />)
    expect(screen.getByTestId('identity-list')).toBeInTheDocument()
  })
})
