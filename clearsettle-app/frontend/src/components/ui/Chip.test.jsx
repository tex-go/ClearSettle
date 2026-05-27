import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Chip, StatusChip } from './Chip'

describe('Chip', () => {
  it('renders children text', () => {
    render(<Chip>Hello</Chip>)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('applies default grey class when no color given', () => {
    render(<Chip>Test</Chip>)
    expect(screen.getByText('Test')).toHaveClass('cs-chip-gr')
  })

  it('applies custom color class', () => {
    render(<Chip color="gn">Active</Chip>)
    expect(screen.getByText('Active')).toHaveClass('cs-chip-gn')
  })

  it('applies cs-chip base class', () => {
    render(<Chip>X</Chip>)
    expect(screen.getByText('X')).toHaveClass('cs-chip')
  })
})

describe('StatusChip', () => {
  it('renders paid status', () => {
    render(<StatusChip status="paid" />)
    expect(screen.getByText('Paid')).toBeInTheDocument()
    expect(screen.getByText('Paid')).toHaveClass('cs-chip-gn')
  })

  it('renders pending status', () => {
    render(<StatusChip status="pending" />)
    expect(screen.getByText('Pending')).toBeInTheDocument()
    expect(screen.getByText('Pending')).toHaveClass('cs-chip-am')
  })

  it('renders unmatched status', () => {
    render(<StatusChip status="unmatched" />)
    expect(screen.getByText('Unmatched')).toHaveClass('cs-chip-rd')
  })

  it('renders won status', () => {
    render(<StatusChip status="won" />)
    expect(screen.getByText('Won')).toHaveClass('cs-chip-gn')
  })

  it('renders lost status', () => {
    render(<StatusChip status="lost" />)
    expect(screen.getByText('Lost')).toHaveClass('cs-chip-rd')
  })

  it('falls back to status text for unknown statuses', () => {
    render(<StatusChip status="custom_status" />)
    expect(screen.getByText('custom_status')).toBeInTheDocument()
  })

  it('falls back to grey class for unknown statuses', () => {
    render(<StatusChip status="unknown" />)
    expect(screen.getByText('unknown')).toHaveClass('cs-chip-gr')
  })

  it('renders partial status', () => {
    render(<StatusChip status="partial" />)
    expect(screen.getByText('Partial')).toBeInTheDocument()
  })

  it('renders disconnected status', () => {
    render(<StatusChip status="disconnected" />)
    expect(screen.getByText('Disconnected')).toHaveClass('cs-chip-gr')
  })
})
