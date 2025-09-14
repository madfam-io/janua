import * as sentryModule from './sentry.config'

describe('sentry', () => {
  it('should export expected functions', () => {
    expect(sentryModule).toBeDefined()
  })
})
