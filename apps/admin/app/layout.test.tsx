import RootLayout from './layout'

// Mock Next.js font
jest.mock('next/font/google', () => ({
  Inter: () => ({
    className: 'mock-inter-font',
  }),
}))

describe('RootLayout', () => {
  it('should export layout component', () => {
    expect(RootLayout).toBeDefined()
    expect(typeof RootLayout).toBe('function')
  })

  it('should have correct metadata export', async () => {
    const { metadata } = await import('./layout')
    expect(metadata.title).toContain('Plinto Admin')
    expect(metadata.description).toContain('Internal superadmin tools')
  })
})
