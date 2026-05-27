import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PasswordInput from './PasswordInput'

function renderInput(props = {}) {
  const defaults = {
    id: 'test-pw',
    label: 'Password *',
    value: '',
    onChange: vi.fn(),
    placeholder: 'Min. 10 characters',
    show: false,
    onToggleShow: vi.fn(),
  }
  return render(<PasswordInput {...defaults} {...props} />)
}

describe('PasswordInput', () => {
  it('renders the label', () => {
    renderInput()
    expect(screen.getByText('Password *')).toBeInTheDocument()
  })

  it('label is linked to input via htmlFor/id', () => {
    renderInput()
    expect(screen.getByLabelText('Password *')).toBeInTheDocument()
  })

  it('renders as type="password" when show=false', () => {
    renderInput({ show: false })
    expect(screen.getByLabelText('Password *')).toHaveAttribute('type', 'password')
  })

  it('renders as type="text" when show=true', () => {
    renderInput({ show: true })
    expect(screen.getByLabelText('Password *')).toHaveAttribute('type', 'text')
  })

  it('eye button has aria-label "Show password" when show=false', () => {
    renderInput({ show: false })
    expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument()
  })

  it('eye button has aria-label "Hide password" when show=true', () => {
    renderInput({ show: true })
    expect(screen.getByRole('button', { name: 'Hide password' })).toBeInTheDocument()
  })

  it('calls onToggleShow when eye button clicked', async () => {
    const onToggleShow = vi.fn()
    renderInput({ onToggleShow })
    await userEvent.click(screen.getByRole('button', { name: /show|hide password/i }))
    expect(onToggleShow).toHaveBeenCalledOnce()
  })

  it('calls onChange when typing', async () => {
    const onChange = vi.fn()
    renderInput({ onChange })
    await userEvent.type(screen.getByLabelText('Password *'), 'abc')
    expect(onChange).toHaveBeenCalled()
  })

  it('displays placeholder text', () => {
    renderInput({ placeholder: 'Enter password here' })
    expect(screen.getByPlaceholderText('Enter password here')).toBeInTheDocument()
  })

  it('sets aria-describedby when ariaDescribedBy provided', () => {
    renderInput({ ariaDescribedBy: 'pw-requirements' })
    expect(screen.getByLabelText('Password *')).toHaveAttribute('aria-describedby', 'pw-requirements')
  })

  it('omits aria-describedby when not provided', () => {
    renderInput()
    expect(screen.getByLabelText('Password *')).not.toHaveAttribute('aria-describedby')
  })

  it('sets aria-invalid=true when ariaInvalid=true', () => {
    renderInput({ ariaInvalid: true })
    expect(screen.getByLabelText('Password *')).toHaveAttribute('aria-invalid', 'true')
  })

  it('omits aria-invalid when not provided', () => {
    renderInput()
    expect(screen.getByLabelText('Password *')).not.toHaveAttribute('aria-invalid')
  })

  it('renders with custom label', () => {
    renderInput({ id: 'confirm', label: 'Confirm Password *' })
    expect(screen.getByLabelText('Confirm Password *')).toBeInTheDocument()
  })

  it('input has autoComplete="new-password"', () => {
    renderInput()
    expect(screen.getByLabelText('Password *')).toHaveAttribute('autocomplete', 'new-password')
  })
})
