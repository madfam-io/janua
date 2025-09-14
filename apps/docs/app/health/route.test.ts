import { GET } from './route'

describe('/health route', () => {
  it('should return healthy status', async () => {
    const response = await GET()
    const data = await response.json()
    
    expect(response.status).toBe(200)
    expect(data.status).toBe('healthy')
    expect(data.service).toBe('docs')
    expect(typeof data.timestamp).toBe('string')
    expect(typeof data.version).toBe('string')
  })

  it('should return valid timestamp', async () => {
    const response = await GET()
    const data = await response.json()
    
    const timestamp = new Date(data.timestamp)
    expect(timestamp.getTime()).not.toBeNaN()
  })
})