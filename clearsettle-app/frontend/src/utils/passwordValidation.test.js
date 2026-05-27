import { describe, it, expect } from 'vitest'
import {
  PASSWORD_RULES,
  checkPassword,
  isPasswordValid,
  friendlyApiError,
} from './passwordValidation'

describe('PASSWORD_RULES', () => {
  it('has exactly 5 rules', () => {
    expect(PASSWORD_RULES).toHaveLength(5)
  })

  it('has unique ids', () => {
    const ids = PASSWORD_RULES.map((r) => r.id)
    expect(new Set(ids).size).toBe(5)
  })

  it('each rule has id, label, and test', () => {
    PASSWORD_RULES.forEach((r) => {
      expect(typeof r.id).toBe('string')
      expect(typeof r.label).toBe('string')
      expect(typeof r.test).toBe('function')
    })
  })
})

describe('checkPassword', () => {
  it('returns array of 5 results', () => {
    expect(checkPassword('')).toHaveLength(5)
  })

  it('all fail for empty string', () => {
    checkPassword('').forEach((r) => expect(r.passed).toBe(false))
  })

  it('all pass for valid password', () => {
    checkPassword('TestPass@1234!').forEach((r) => expect(r.passed).toBe(true))
  })

  it('len rule passes at exactly 10 chars', () => {
    const results = checkPassword('Abcde@1234')
    const len = results.find((r) => r.id === 'len')
    expect(len.passed).toBe(true)
  })

  it('len rule fails at 9 chars', () => {
    const results = checkPassword('Abcde@123')
    const len = results.find((r) => r.id === 'len')
    expect(len.passed).toBe(false)
  })

  it('upper rule fails when no uppercase', () => {
    const results = checkPassword('testpass@1')
    const upper = results.find((r) => r.id === 'upper')
    expect(upper.passed).toBe(false)
  })

  it('upper rule passes with uppercase', () => {
    const results = checkPassword('Testpass@1')
    const upper = results.find((r) => r.id === 'upper')
    expect(upper.passed).toBe(true)
  })

  it('digit rule fails when no digit', () => {
    const results = checkPassword('TestPass@abc')
    const digit = results.find((r) => r.id === 'digit')
    expect(digit.passed).toBe(false)
  })

  it('special rule fails when no special char', () => {
    const results = checkPassword('TestPass1234')
    const special = results.find((r) => r.id === 'special')
    expect(special.passed).toBe(false)
  })

  it('special rule passes with @ symbol', () => {
    const results = checkPassword('TestPass@123')
    const special = results.find((r) => r.id === 'special')
    expect(special.passed).toBe(true)
  })

  it('result objects have id, label, passed', () => {
    const results = checkPassword('TestPass@1234!')
    results.forEach((r) => {
      expect(r).toHaveProperty('id')
      expect(r).toHaveProperty('label')
      expect(r).toHaveProperty('passed')
    })
  })
})

describe('isPasswordValid', () => {
  it('returns false for empty string', () => {
    expect(isPasswordValid('')).toBe(false)
  })

  it('returns false for weak password', () => {
    expect(isPasswordValid('weak')).toBe(false)
  })

  it('returns true for strong password', () => {
    expect(isPasswordValid('TestPass@1234!')).toBe(true)
  })

  it('returns false when missing uppercase', () => {
    expect(isPasswordValid('testpass@1234!')).toBe(false)
  })

  it('returns false when missing digit', () => {
    expect(isPasswordValid('TestPass@abc!')).toBe(false)
  })

  it('returns false when missing special char', () => {
    expect(isPasswordValid('TestPass12345')).toBe(false)
  })

  it('returns false when too short', () => {
    expect(isPasswordValid('Tp@1')).toBe(false)
  })
})

describe('friendlyApiError', () => {
  it('returns fallback for null detail', () => {
    expect(friendlyApiError(null)).toContain('Registration failed')
  })

  it('returns fallback for undefined', () => {
    expect(friendlyApiError(undefined)).toContain('Registration failed')
  })

  it('maps array detail with password length error', () => {
    const msg = friendlyApiError([{ msg: 'At least 10 characters required' }])
    expect(msg).toContain('10 characters')
  })

  it('maps array detail with uppercase error', () => {
    const msg = friendlyApiError([{ msg: 'uppercase letter required' }])
    expect(msg).toContain('uppercase')
  })

  it('maps array detail with lowercase error', () => {
    const msg = friendlyApiError([{ msg: 'lowercase letter required' }])
    expect(msg).toContain('lowercase')
  })

  it('maps array detail with digit error', () => {
    const msg = friendlyApiError([{ msg: 'digit required' }])
    expect(msg).toContain('number')
  })

  it('maps array detail with special char error', () => {
    const msg = friendlyApiError([{ msg: 'special character required' }])
    expect(msg).toContain('special')
  })

  it('maps string detail for already-registered email', () => {
    const msg = friendlyApiError('Email already registered')
    expect(msg).toContain('already exists')
  })

  it('returns raw string detail when unrecognised', () => {
    const msg = friendlyApiError('Some custom backend message')
    expect(msg).toBe('Some custom backend message')
  })

  it('maps GSTIN error from array', () => {
    const msg = friendlyApiError([{ msg: 'Invalid gstin format' }])
    expect(msg).toContain('GSTIN')
  })
})
