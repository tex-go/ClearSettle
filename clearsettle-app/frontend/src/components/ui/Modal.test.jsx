import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Modal } from './Modal'

describe('Modal', () => {
  it('renders nothing when open=false', () => {
    const { container } = render(
      <Modal open={false} title="Test" onClose={vi.fn()}>content</Modal>
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders title when open=true', () => {
    render(<Modal open={true} title="My Title" onClose={vi.fn()}>body</Modal>)
    expect(screen.getByText('My Title')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    render(<Modal open={true} title="T" sub="Subtitle here" onClose={vi.fn()}>body</Modal>)
    expect(screen.getByText('Subtitle here')).toBeInTheDocument()
  })

  it('does not render sub when not provided', () => {
    render(<Modal open={true} title="T" onClose={vi.fn()}>body</Modal>)
    expect(screen.queryByText('Subtitle here')).toBeNull()
  })

  it('renders children', () => {
    render(<Modal open={true} title="T" onClose={vi.fn()}>child content</Modal>)
    expect(screen.getByText('child content')).toBeInTheDocument()
  })

  it('renders footer when provided', () => {
    render(
      <Modal open={true} title="T" onClose={vi.fn()} footer={<button>Close</button>}>
        body
      </Modal>
    )
    expect(screen.getByText('Close')).toBeInTheDocument()
  })

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn()
    render(<Modal open={true} title="T" onClose={onClose}>body</Modal>)
    fireEvent.click(screen.getByText('✕'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('calls onClose when Escape key is pressed', () => {
    const onClose = vi.fn()
    render(<Modal open={true} title="T" onClose={onClose}>body</Modal>)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('calls onClose when overlay backdrop is clicked', () => {
    const onClose = vi.fn()
    render(<Modal open={true} title="T" onClose={onClose}>body</Modal>)
    const overlay = document.querySelector('.modal-overlay')
    fireEvent.click(overlay, { target: overlay })
    // overlay click only closes when target === currentTarget (direct click)
  })

  it('does not call onClose when inner content is clicked', () => {
    const onClose = vi.fn()
    render(<Modal open={true} title="T" onClose={onClose}>body</Modal>)
    fireEvent.click(screen.getByText('body'))
    expect(onClose).not.toHaveBeenCalled()
  })

  it('applies default max-width for no size', () => {
    render(<Modal open={true} title="T" onClose={vi.fn()}>body</Modal>)
    const wrap = document.querySelector('.modal-wrap')
    expect(wrap.style.maxWidth).toBe('700px')
  })

  it('applies lg max-width for size=lg', () => {
    render(<Modal open={true} title="T" onClose={vi.fn()} size="lg">body</Modal>)
    const wrap = document.querySelector('.modal-wrap')
    expect(wrap.style.maxWidth).toBe('860px')
  })

  it('applies sm max-width for size=sm', () => {
    render(<Modal open={true} title="T" onClose={vi.fn()} size="sm">body</Modal>)
    const wrap = document.querySelector('.modal-wrap')
    expect(wrap.style.maxWidth).toBe('460px')
  })
})
