import React from 'react'
import { render } from '@testing-library/react'
import { SearchModal } from './search-modal'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

describe('SearchModal', () => {
  it('should render without crashing', () => {
    render(<SearchModal isOpen={true} onClose={() => {}} />)
  })
})
