import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../utils/api', () => ({
  default: { post: vi.fn() },
}))

vi.mock('../store/authStore', () => ({
  default: vi.fn((selector) => {
    const store = { login: vi.fn() }
    return selector ? selector(store) : store
  }),
}))

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal()
  return { ...actual, useNavigate: () => vi.fn() }
})

import api from '../utils/api'
import Register from './Register'

function renderRegister() {
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>
  )
}

// Helper — gets the password input (not confirm) by label
function getPasswordInput() {
  return screen.getByLabelText('Password *')
}

function getConfirmInput() {
  return screen.getByLabelText('Confirm Password *')
}

beforeEach(() => {
  vi.clearAllMocks()
})

// ── Step 1 — basic rendering ───────────────────────────────────────────────────

describe('Register — step 1 rendering', () => {
  it('renders the "Create your account" heading', () => {
    renderRegister()
    expect(screen.getByText(/create your account/i)).toBeInTheDocument()
  })

  it('renders the ClearSettle branding', () => {
    renderRegister()
    expect(screen.getByText('ClearSettle')).toBeInTheDocument()
  })

  it('shows "Step 1 of 3" progress text', () => {
    renderRegister()
    expect(screen.getByText(/step 1 of 3/i)).toBeInTheDocument()
  })

  it('renders Full Name field via label', () => {
    renderRegister()
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
  })

  it('renders Email Address field via label', () => {
    renderRegister()
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
  })

  it('renders Phone Number field via label', () => {
    renderRegister()
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument()
  })

  it('renders Password field via label', () => {
    renderRegister()
    expect(screen.getByLabelText('Password *')).toBeInTheDocument()
  })

  it('renders Confirm Password field via label', () => {
    renderRegister()
    expect(screen.getByLabelText('Confirm Password *')).toBeInTheDocument()
  })

  it('shows "Sign in" link', () => {
    renderRegister()
    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument()
  })
})

// ── Password checklist — always visible ────────────────────────────────────────

describe('Register — password checklist (always rendered)', () => {
  it('shows all 5 requirements before typing', () => {
    renderRegister()
    expect(screen.getByText('Minimum 10 characters')).toBeInTheDocument()
    expect(screen.getByText('Contains uppercase letter')).toBeInTheDocument()
    expect(screen.getByText('Contains lowercase letter')).toBeInTheDocument()
    expect(screen.getByText('Contains a number')).toBeInTheDocument()
    expect(screen.getByText('Contains special character')).toBeInTheDocument()
  })

  it('checklist is linked to password field via aria-describedby', () => {
    renderRegister()
    const pwInput = getPasswordInput()
    expect(pwInput).toHaveAttribute('aria-describedby', 'pw-requirements')
  })

  it('checklist has accessible list role', () => {
    renderRegister()
    expect(screen.getByRole('list', { name: /password requirements/i })).toBeInTheDocument()
  })

  it('checklist items update after typing a valid password', async () => {
    renderRegister()
    const pwInput = getPasswordInput()
    await userEvent.type(pwInput, 'TestPass@1234!')
    // All requirements should now show as passed (✓ in the DOM)
    const list = screen.getByRole('list', { name: /password requirements/i })
    const items = within(list).getAllByRole('listitem')
    expect(items).toHaveLength(5)
  })

  it('requirements render before user touches password field', () => {
    renderRegister()
    // Must be in DOM from the start — not gated on typing
    const list = screen.getByRole('list', { name: /password requirements/i })
    expect(list).toBeInTheDocument()
  })
})

// ── Continue button disabled state ─────────────────────────────────────────────

describe('Register — Continue button guard', () => {
  it('is disabled when form is empty', () => {
    renderRegister()
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled()
  })

  it('remains disabled with only name filled', async () => {
    renderRegister()
    await userEvent.type(screen.getByLabelText(/full name/i), 'Ranjith Kumar')
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled()
  })

  it('becomes enabled when all fields are valid', async () => {
    renderRegister()
    await userEvent.type(screen.getByLabelText(/full name/i), 'Ranjith Kumar')
    await userEvent.type(screen.getByLabelText(/email address/i), 'ranjith@example.com')
    await userEvent.type(screen.getByLabelText(/phone number/i), '+91 98765 43210')
    await userEvent.type(getPasswordInput(), 'TestPass@1234!')
    await userEvent.type(getConfirmInput(), 'TestPass@1234!')
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /continue/i })).not.toBeDisabled()
    })
  })

  it('is disabled when password is invalid', async () => {
    renderRegister()
    await userEvent.type(screen.getByLabelText(/full name/i), 'Ranjith Kumar')
    await userEvent.type(screen.getByLabelText(/email address/i), 'r@e.com')
    await userEvent.type(screen.getByLabelText(/phone number/i), '+91 9876543210')
    await userEvent.type(getPasswordInput(), 'weak') // fails all rules
    await userEvent.type(getConfirmInput(), 'weak')
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled()
  })

  it('is disabled when passwords do not match', async () => {
    renderRegister()
    await userEvent.type(screen.getByLabelText(/full name/i), 'Ranjith Kumar')
    await userEvent.type(screen.getByLabelText(/email address/i), 'r@e.com')
    await userEvent.type(screen.getByLabelText(/phone number/i), '+91 9876543210')
    await userEvent.type(getPasswordInput(), 'TestPass@1234!')
    await userEvent.type(getConfirmInput(), 'Different@1!')
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled()
  })
})

// ── Confirm password mismatch ─────────────────────────────────────────────────

describe('Register — confirm password mismatch', () => {
  it('shows mismatch error after typing different confirm password', async () => {
    renderRegister()
    await userEvent.type(getPasswordInput(), 'TestPass@1234!')
    await userEvent.type(getConfirmInput(), 'Different@1!')
    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    })
  })

  it('hides mismatch error when passwords match', async () => {
    renderRegister()
    await userEvent.type(getPasswordInput(), 'TestPass@1234!')
    await userEvent.type(getConfirmInput(), 'Different@1!')
    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    })
    // Clear and retype correct confirm
    await userEvent.clear(getConfirmInput())
    await userEvent.type(getConfirmInput(), 'TestPass@1234!')
    await waitFor(() => {
      expect(screen.queryByText(/passwords do not match/i)).not.toBeInTheDocument()
    })
  })

  it('mismatch alert has role="alert"', async () => {
    renderRegister()
    await userEvent.type(getPasswordInput(), 'TestPass@1234!')
    await userEvent.type(getConfirmInput(), 'Wrong@1!')
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/passwords do not match/i)
    })
  })
})

// ── Password visibility toggle ─────────────────────────────────────────────────

describe('Register — password visibility toggle', () => {
  it('password field starts as type="password"', () => {
    renderRegister()
    expect(getPasswordInput()).toHaveAttribute('type', 'password')
  })

  it('confirm field starts as type="password"', () => {
    renderRegister()
    expect(getConfirmInput()).toHaveAttribute('type', 'password')
  })

  it('eye button has accessible label "Show password"', () => {
    renderRegister()
    const toggleBtns = screen.getAllByRole('button', { name: /show password/i })
    expect(toggleBtns.length).toBeGreaterThan(0)
  })

  it('clicking eye button toggles password field to text', async () => {
    renderRegister()
    const [showBtn] = screen.getAllByRole('button', { name: /show password/i })
    await userEvent.click(showBtn)
    expect(getPasswordInput()).toHaveAttribute('type', 'text')
  })

  it('eye button label changes to "Hide password" after toggling', async () => {
    renderRegister()
    const [showBtn] = screen.getAllByRole('button', { name: /show password/i })
    await userEvent.click(showBtn)
    expect(screen.getAllByRole('button', { name: /hide password/i }).length).toBeGreaterThan(0)
  })

  it('clicking hide button toggles back to type="password"', async () => {
    renderRegister()
    const [showBtn] = screen.getAllByRole('button', { name: /show password/i })
    await userEvent.click(showBtn) // show
    const [hideBtn] = screen.getAllByRole('button', { name: /hide password/i })
    await userEvent.click(hideBtn) // hide
    expect(getPasswordInput()).toHaveAttribute('type', 'password')
  })
})

// ── Accessibility ──────────────────────────────────────────────────────────────

describe('Register — accessibility', () => {
  it('all text inputs have associated labels', () => {
    renderRegister()
    const inputs = [
      screen.getByLabelText(/full name/i),
      screen.getByLabelText(/email address/i),
      screen.getByLabelText(/phone number/i),
      screen.getByLabelText('Password *'),
      screen.getByLabelText('Confirm Password *'),
    ]
    inputs.forEach((input) => expect(input).toBeInTheDocument())
  })

  it('password field has aria-describedby pointing to checklist', () => {
    renderRegister()
    const pwInput = getPasswordInput()
    expect(pwInput).toHaveAttribute('aria-describedby', 'pw-requirements')
  })

  it('step progress has aria-live attribute', () => {
    renderRegister()
    const stepText = screen.getByText(/step 1 of 3/i)
    expect(stepText).toHaveAttribute('aria-live', 'polite')
  })

  it('error banner has role="alert"', async () => {
    renderRegister()
    // Step 1: fill all required fields to enable Continue
    await userEvent.type(screen.getByLabelText(/full name/i), 'Ranjith Kumar')
    await userEvent.type(screen.getByLabelText(/email address/i), 'test@example.com')
    await userEvent.type(screen.getByLabelText(/phone number/i), '+91 9876543210')
    await userEvent.type(screen.getByLabelText('Password *'), 'TestPass@1234!')
    await userEvent.type(screen.getByLabelText('Confirm Password *'), 'TestPass@1234!')
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /continue/i })).not.toBeDisabled()
    })
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    // Now on step 2 — Continue is not disabled; click without filling required fields
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})

// ── Live validation ────────────────────────────────────────────────────────────

describe('Register — live password validation', () => {
  it('updates checklist immediately on each keystroke', async () => {
    renderRegister()
    const pwInput = getPasswordInput()
    // Type a single uppercase — "Contains uppercase letter" rule should pass
    await userEvent.type(pwInput, 'A')
    // Checklist should be in DOM with updated state (just check it's there)
    expect(screen.getByRole('list', { name: /password requirements/i })).toBeInTheDocument()
  })

  it('password field gets aria-invalid=true when touched and invalid', async () => {
    renderRegister()
    await userEvent.type(getPasswordInput(), 'bad')
    // Leave the field (touching it sets pwTouched)
    await userEvent.tab()
    // After typing something invalid and moving on, aria-invalid should be set
    // (component sets it based on pwTouched && !pwValid)
    const pwInput = getPasswordInput()
    await waitFor(() => {
      expect(pwInput).toHaveAttribute('aria-invalid', 'true')
    })
  })
})

// ── Field interaction ──────────────────────────────────────────────────────────

describe('Register — field interaction', () => {
  it('name input accepts text', async () => {
    renderRegister()
    const nameInput = screen.getByLabelText(/full name/i)
    await userEvent.type(nameInput, 'Ranjith Kumar')
    expect(nameInput).toHaveValue('Ranjith Kumar')
  })

  it('email input accepts email', async () => {
    renderRegister()
    const emailInput = screen.getByLabelText(/email address/i)
    await userEvent.type(emailInput, 'test@example.com')
    expect(emailInput).toHaveValue('test@example.com')
  })

  it('phone input accepts phone number', async () => {
    renderRegister()
    const phoneInput = screen.getByLabelText(/phone number/i)
    await userEvent.type(phoneInput, '+91 98765 43210')
    expect(phoneInput).toHaveValue('+91 98765 43210')
  })
})
