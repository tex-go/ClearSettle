import { describe, it, expect, beforeEach, vi } from 'vitest'
import useUIStore from './uiStore'

beforeEach(() => {
  useUIStore.setState({ toasts: [] })
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('uiStore — addToast', () => {
  it('adds a toast to the list', () => {
    useUIStore.getState().addToast('Hello', 'success')
    expect(useUIStore.getState().toasts).toHaveLength(1)
    expect(useUIStore.getState().toasts[0].msg).toBe('Hello')
    expect(useUIStore.getState().toasts[0].type).toBe('success')
  })

  it('defaults type to info when not provided', () => {
    useUIStore.getState().addToast('Hey')
    expect(useUIStore.getState().toasts[0].type).toBe('info')
  })

  it('stores sub message', () => {
    useUIStore.getState().addToast('Main', 'warn', 'Sub text')
    expect(useUIStore.getState().toasts[0].sub).toBe('Sub text')
  })

  it('generates unique id per toast', () => {
    useUIStore.getState().addToast('A')
    useUIStore.getState().addToast('B')
    const toasts = useUIStore.getState().toasts
    expect(toasts[0].id).not.toBe(toasts[1].id)
  })

  it('adds multiple toasts independently', () => {
    useUIStore.getState().addToast('A', 'success')
    useUIStore.getState().addToast('B', 'error')
    useUIStore.getState().addToast('C', 'info')
    expect(useUIStore.getState().toasts).toHaveLength(3)
  })

  it('auto-removes toast after 4 seconds', () => {
    useUIStore.getState().addToast('Temp', 'info')
    expect(useUIStore.getState().toasts).toHaveLength(1)
    vi.advanceTimersByTime(4001)
    expect(useUIStore.getState().toasts).toHaveLength(0)
  })

  it('does not remove toast before 4 seconds', () => {
    useUIStore.getState().addToast('Temp', 'info')
    vi.advanceTimersByTime(3999)
    expect(useUIStore.getState().toasts).toHaveLength(1)
  })
})

describe('uiStore — removeToast', () => {
  it('removes a toast by id', () => {
    useUIStore.getState().addToast('Msg', 'success')
    const id = useUIStore.getState().toasts[0].id
    useUIStore.getState().removeToast(id)
    expect(useUIStore.getState().toasts).toHaveLength(0)
  })

  it('only removes the matching toast', () => {
    useUIStore.getState().addToast('A')
    useUIStore.getState().addToast('B')
    const id = useUIStore.getState().toasts[0].id
    useUIStore.getState().removeToast(id)
    expect(useUIStore.getState().toasts).toHaveLength(1)
    expect(useUIStore.getState().toasts[0].msg).toBe('B')
  })

  it('is a no-op for non-existent id', () => {
    useUIStore.getState().addToast('A')
    useUIStore.getState().removeToast('fake-id-999')
    expect(useUIStore.getState().toasts).toHaveLength(1)
  })
})
