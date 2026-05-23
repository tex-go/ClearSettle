import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ToastContainer } from './Toast'
import useUIStore from '../../store/uiStore'

beforeEach(() => {
  useUIStore.setState({ toasts: [] })
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('ToastContainer — empty state', () => {
  it('renders without crashing when there are no toasts', () => {
    const { container } = render(<ToastContainer />)
    expect(container.querySelector('.toast-container')).toBeInTheDocument()
  })

  it('renders no toast items when store is empty', () => {
    render(<ToastContainer />)
    expect(document.querySelectorAll('.toast-item')).toHaveLength(0)
  })

  it('has role=log and aria-live=polite', () => {
    render(<ToastContainer />)
    const log = screen.getByRole('log')
    expect(log).toHaveAttribute('aria-live', 'polite')
  })
})

describe('ToastContainer — rendering toasts', () => {
  it('renders a toast message added to the store', () => {
    render(<ToastContainer />)
    useUIStore.getState().addToast('Settlement synced', 'success')
    // Re-render happens via store subscription
    render(<ToastContainer />)
    expect(screen.getByText('Settlement synced')).toBeInTheDocument()
  })

  it('renders sub text when provided', () => {
    useUIStore.getState().addToast('Sync done', 'info', '42 records imported')
    render(<ToastContainer />)
    expect(screen.getByText('42 records imported')).toBeInTheDocument()
  })

  it('renders each toast with role=alert', () => {
    useUIStore.getState().addToast('A', 'error')
    useUIStore.getState().addToast('B', 'warn')
    render(<ToastContainer />)
    const alerts = screen.getAllByRole('alert')
    expect(alerts.length).toBeGreaterThanOrEqual(2)
  })

  it('applies info border colour by default', () => {
    useUIStore.getState().addToast('Info msg')
    render(<ToastContainer />)
    const item = document.querySelector('.toast-item')
    expect(item.style.borderLeft).toContain('#0ABFCA')
  })

  it('applies success border colour', () => {
    useUIStore.getState().addToast('OK', 'success')
    render(<ToastContainer />)
    const item = document.querySelector('.toast-item')
    expect(item.style.borderLeft).toContain('#0DB07A')
  })

  it('applies error border colour', () => {
    useUIStore.getState().addToast('Fail', 'error')
    render(<ToastContainer />)
    const item = document.querySelector('.toast-item')
    expect(item.style.borderLeft).toContain('#E8344A')
  })

  it('applies warn border colour', () => {
    useUIStore.getState().addToast('Warn', 'warn')
    render(<ToastContainer />)
    const item = document.querySelector('.toast-item')
    expect(item.style.borderLeft).toContain('#E9930D')
  })
})

describe('ToastContainer — interaction', () => {
  it('removes toast from store when clicked', () => {
    useUIStore.getState().addToast('Click me', 'info')
    render(<ToastContainer />)
    const item = document.querySelector('.toast-item')
    fireEvent.click(item)
    expect(useUIStore.getState().toasts).toHaveLength(0)
  })

  it('leaves other toasts untouched when one is clicked', () => {
    useUIStore.getState().addToast('A', 'info')
    useUIStore.getState().addToast('B', 'success')
    render(<ToastContainer />)
    const items = document.querySelectorAll('.toast-item')
    fireEvent.click(items[0])
    expect(useUIStore.getState().toasts).toHaveLength(1)
    expect(useUIStore.getState().toasts[0].msg).toBe('B')
  })
})
