import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

// Mock the api module before importing useApi
vi.mock('../utils/api', () => ({
  default: {
    get: vi.fn(),
  },
}))

import api from '../utils/api'
import useApi from './useApi'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useApi', () => {
  it('starts with loading=true and data=null', () => {
    api.get.mockReturnValue(new Promise(() => {})) // never resolves
    const { result } = renderHook(() => useApi('/test'))
    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('sets data on successful response', async () => {
    api.get.mockResolvedValue({ data: { items: [1, 2, 3] } })
    const { result } = renderHook(() => useApi('/test'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ items: [1, 2, 3] })
    expect(result.current.error).toBeNull()
  })

  it('sets error on failed request', async () => {
    const err = new Error('Network error')
    api.get.mockRejectedValue(err)
    const { result } = renderHook(() => useApi('/test'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBe(err)
  })

  it('calls api.get with the provided url', async () => {
    api.get.mockResolvedValue({ data: {} })
    renderHook(() => useApi('/my-endpoint'))
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/my-endpoint'))
  })

  it('does not fetch when url is null', () => {
    renderHook(() => useApi(null))
    expect(api.get).not.toHaveBeenCalled()
  })

  it('does not fetch when url is empty string', () => {
    renderHook(() => useApi(''))
    expect(api.get).not.toHaveBeenCalled()
  })

  it('re-fetches when url changes', async () => {
    api.get.mockResolvedValue({ data: { v: 1 } })
    const { rerender } = renderHook(({ url }) => useApi(url), {
      initialProps: { url: '/first' },
    })
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/first'))

    api.get.mockResolvedValue({ data: { v: 2 } })
    rerender({ url: '/second' })
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/second'))
    expect(api.get).toHaveBeenCalledTimes(2)
  })
})
