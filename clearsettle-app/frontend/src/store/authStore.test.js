import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Reset module between tests so the store re-initialises from localStorage
beforeEach(() => {
  localStorage.clear()
  vi.resetModules()
})

afterEach(() => {
  localStorage.clear()
})

async function getStore() {
  const mod = await import('./authStore')
  return mod.default
}

describe('authStore — initial state', () => {
  it('starts unauthenticated when localStorage is empty', async () => {
    const useAuthStore = await getStore()
    const state = useAuthStore.getState()
    expect(state.isAuth).toBe(false)
    expect(state.token).toBeNull()
    expect(state.user).toBeNull()
  })

  it('rehydrates from localStorage', async () => {
    localStorage.setItem('cs_token', 'tok123')
    localStorage.setItem('cs_user', JSON.stringify({ email: 'a@b.com' }))
    const useAuthStore = await getStore()
    const state = useAuthStore.getState()
    expect(state.token).toBe('tok123')
    expect(state.user?.email).toBe('a@b.com')
    expect(state.isAuth).toBe(true)
  })

  it('handles corrupted user JSON gracefully', async () => {
    localStorage.setItem('cs_token', 'tok')
    localStorage.setItem('cs_user', '{broken json')
    const useAuthStore = await getStore()
    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
  })
})

describe('authStore — login', () => {
  it('sets token and isAuth on login', async () => {
    const useAuthStore = await getStore()
    const { login } = useAuthStore.getState()
    login('access-tok', 'refresh-tok', { email: 'u@e.com' })
    const state = useAuthStore.getState()
    expect(state.token).toBe('access-tok')
    expect(state.refreshToken).toBe('refresh-tok')
    expect(state.isAuth).toBe(true)
    expect(state.user.email).toBe('u@e.com')
  })

  it('persists token to localStorage', async () => {
    const useAuthStore = await getStore()
    useAuthStore.getState().login('my-token', 'my-refresh', { email: 'x@y.com' })
    expect(localStorage.getItem('cs_token')).toBe('my-token')
    expect(localStorage.getItem('cs_refresh_token')).toBe('my-refresh')
  })
})

describe('authStore — setTokens', () => {
  it('updates tokens without clearing user', async () => {
    const useAuthStore = await getStore()
    useAuthStore.getState().login('old-tok', 'old-ref', { email: 'u@e.com' })
    useAuthStore.getState().setTokens('new-tok', 'new-ref')
    const state = useAuthStore.getState()
    expect(state.token).toBe('new-tok')
    expect(state.refreshToken).toBe('new-ref')
    expect(state.user.email).toBe('u@e.com') // user unchanged
  })

  it('preserves old refresh token if null passed', async () => {
    const useAuthStore = await getStore()
    useAuthStore.getState().login('t', 'old-ref', { email: 'u@e.com' })
    useAuthStore.getState().setTokens('new-tok', null)
    const state = useAuthStore.getState()
    expect(state.refreshToken).toBe('old-ref')
  })
})

describe('authStore — logout', () => {
  it('clears all state on logout', async () => {
    const useAuthStore = await getStore()
    useAuthStore.getState().login('tok', 'ref', { email: 'u@e.com' })
    useAuthStore.getState().logout()
    const state = useAuthStore.getState()
    expect(state.token).toBeNull()
    expect(state.refreshToken).toBeNull()
    expect(state.user).toBeNull()
    expect(state.isAuth).toBe(false)
  })

  it('removes all keys from localStorage on logout', async () => {
    const useAuthStore = await getStore()
    useAuthStore.getState().login('tok', 'ref', { email: 'u@e.com' })
    localStorage.setItem('cs_onboarded', '1')
    useAuthStore.getState().logout()
    expect(localStorage.getItem('cs_token')).toBeNull()
    expect(localStorage.getItem('cs_refresh_token')).toBeNull()
    expect(localStorage.getItem('cs_user')).toBeNull()
    expect(localStorage.getItem('cs_onboarded')).toBeNull()
  })
})
