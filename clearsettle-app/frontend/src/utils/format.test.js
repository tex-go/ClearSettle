import { describe, it, expect } from 'vitest'
import { INR, INRL, INRCR, PCT, statusColors } from './format'

describe('INR', () => {
  it('formats a positive integer', () => {
    expect(INR(1000)).toBe('₹1,000')
  })

  it('formats zero', () => {
    expect(INR(0)).toBe('₹0')
  })

  it('returns ₹0 for null', () => {
    expect(INR(null)).toBe('₹0')
  })

  it('returns ₹0 for undefined', () => {
    expect(INR(undefined)).toBe('₹0')
  })

  it('handles large amounts with Indian formatting', () => {
    const result = INR(100000)
    expect(result).toContain('₹')
    expect(result).toContain('1,00,000')
  })

  it('handles decimal amounts', () => {
    const result = INR(1234.56)
    expect(result).toContain('₹')
  })

  it('handles negative amounts', () => {
    const result = INR(-500)
    expect(result).toContain('₹')
  })
})

describe('INRL', () => {
  it('returns ₹0 for falsy input', () => {
    expect(INRL(0)).toBe('₹0')
    expect(INRL(null)).toBe('₹0')
  })

  it('formats lakhs correctly', () => {
    const result = INRL(200000)
    expect(result).toContain('L')
    expect(result).toContain('2.00')
  })

  it('formats crores correctly', () => {
    const result = INRL(20000000)
    expect(result).toContain('Cr')
    expect(result).toContain('2.00')
  })

  it('uses INR for values below 1 lakh', () => {
    const result = INRL(50000)
    expect(result).toContain('₹')
    expect(result).not.toContain('L')
    expect(result).not.toContain('Cr')
  })
})

describe('INRCR', () => {
  it('returns ₹0 for falsy input', () => {
    expect(INRCR(0)).toBe('₹0')
  })

  it('formats crores', () => {
    const result = INRCR(10000000)
    expect(result).toContain('Cr')
  })

  it('delegates to INRL for smaller amounts', () => {
    const result = INRCR(200000)
    expect(result).toContain('L')
  })
})

describe('PCT', () => {
  it('formats percentage with 1 decimal', () => {
    expect(PCT(12.5)).toBe('12.5%')
  })

  it('formats zero', () => {
    expect(PCT(0)).toBe('0.0%')
  })

  it('rounds to 1 decimal', () => {
    expect(PCT(33.333)).toBe('33.3%')
  })

  it('handles negative percentages', () => {
    expect(PCT(-5.5)).toBe('-5.5%')
  })

  it('handles 100', () => {
    expect(PCT(100)).toBe('100.0%')
  })
})

describe('statusColors', () => {
  it('has expected keys', () => {
    expect(statusColors.paid).toBe('gn')
    expect(statusColors.pending).toBe('am')
    expect(statusColors.unmatched).toBe('rd')
    expect(statusColors.won).toBe('gn')
    expect(statusColors.lost).toBe('rd')
  })

  it('is an object', () => {
    expect(typeof statusColors).toBe('object')
  })
})
