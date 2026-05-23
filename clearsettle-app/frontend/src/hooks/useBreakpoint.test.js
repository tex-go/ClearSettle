import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import useBreakpoint from './useBreakpoint'

function setWidth(w) {
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: w })
  window.dispatchEvent(new Event('resize'))
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useBreakpoint', () => {
  it('returns mobile=true for width 375', () => {
    setWidth(375)
    const { result } = renderHook(() => useBreakpoint())
    expect(result.current.isMobile).toBe(true)
    expect(result.current.isDesktop).toBe(false)
  })

  it('returns isDesktop=true for width 1280', () => {
    setWidth(1280)
    const { result } = renderHook(() => useBreakpoint())
    expect(result.current.isDesktop).toBe(true)
    expect(result.current.isMobile).toBe(false)
  })

  it('returns isTablet=true for width 768', () => {
    setWidth(768)
    const { result } = renderHook(() => useBreakpoint())
    expect(result.current.isTablet).toBe(true)
    expect(result.current.isMobile).toBe(false)
    expect(result.current.isDesktop).toBe(false)
  })

  it('returns isXs=true for width 400', () => {
    setWidth(400)
    const { result } = renderHook(() => useBreakpoint())
    expect(result.current.isXs).toBe(true)
  })

  it('returns isSm=true for width 480', () => {
    setWidth(480)
    const { result } = renderHook(() => useBreakpoint())
    expect(result.current.isSm).toBe(true)
    expect(result.current.isXs).toBe(false)
  })

  it('returns is2xl=true for width 1440', () => {
    setWidth(1440)
    const { result } = renderHook(() => useBreakpoint())
    expect(result.current.is2xl).toBe(true)
  })

  it('updates state after resize event (debounced)', async () => {
    setWidth(1200)
    const { result } = renderHook(() => useBreakpoint())
    expect(result.current.isDesktop).toBe(true)

    act(() => { setWidth(375) })
    act(() => { vi.advanceTimersByTime(100) })
    expect(result.current.isMobile).toBe(true)
  })

  it('exposes width as a number', () => {
    setWidth(1024)
    const { result } = renderHook(() => useBreakpoint())
    expect(typeof result.current.width).toBe('number')
    expect(result.current.width).toBe(1024)
  })

  it('isLg=true for width 1024', () => {
    setWidth(1024)
    const { result } = renderHook(() => useBreakpoint())
    expect(result.current.isLg).toBe(true)
    expect(result.current.isXl).toBe(false)
  })
})
