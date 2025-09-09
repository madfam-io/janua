import { cn } from '@/lib/utils'

describe('utils', () => {
  describe('cn', () => {
    it('should merge class names correctly', () => {
      expect(cn('px-2 py-1', 'px-3')).toBe('py-1 px-3')
    })

    it('should handle conditional classes', () => {
      expect(cn('px-2', true && 'py-1', false && 'invisible')).toBe('px-2 py-1')
    })

    it('should handle empty inputs', () => {
      expect(cn()).toBe('')
      expect(cn('')).toBe('')
      expect(cn(null, undefined)).toBe('')
    })

    it('should handle arrays', () => {
      expect(cn(['px-2', 'py-1'])).toBe('px-2 py-1')
      expect(cn(['px-2'], ['py-1'])).toBe('px-2 py-1')
    })

    it('should handle objects', () => {
      expect(cn({ 'px-2': true, 'py-1': false })).toBe('px-2')
      expect(cn({ 'px-2': true }, { 'py-1': true })).toBe('px-2 py-1')
    })

    it('should merge tailwind conflicting classes', () => {
      // Test tailwind-merge functionality
      expect(cn('p-4', 'p-2')).toBe('p-2')
      expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500')
    })

    it('should handle complex combinations', () => {
      const result = cn(
        'px-2 py-1',
        true && 'bg-blue-500',
        { 'text-white': true, 'text-black': false },
        ['font-bold'],
        'px-4' // Should override px-2
      )
      expect(result).toBe('py-1 bg-blue-500 text-white font-bold px-4')
    })
  })
})