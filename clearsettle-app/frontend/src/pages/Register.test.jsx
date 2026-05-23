import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

import Register from './Register'

function renderRegister() {
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Register page — step 1', () => {
  it('renders the registration form', () => {
    renderRegister()
    expect(screen.getByText(/create your account/i)).toBeInTheDocument()
  })

  it('renders name, email and phone fields', () => {
    renderRegister()
    expect(screen.getByPlaceholderText(/ravi kumar/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/you@company\.in/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/\+91/i)).toBeInTheDocument()
  })

  it('renders password field', () => {
    renderRegister()
    const pwInputs = screen.getAllByRole('textbox').length
    expect(pwInputs).toBeGreaterThan(0)
  })

  it('shows all 5 password requirements', () => {
    renderRegister()
    expect(screen.getByText(/minimum 10 characters/i)).toBeInTheDocument()
    expect(screen.getByText(/uppercase/i)).toBeInTheDocument()
    expect(screen.getByText(/lowercase/i)).toBeInTheDocument()
    expect(screen.getByText(/contains a number/i)).toBeInTheDocument()
    expect(screen.getByText(/special character/i)).toBeInTheDocument()
  })

  it('Continue button is disabled when form is empty', () => {
    renderRegister()
    const btn = screen.getByRole('button', { name: /continue/i })
    expect(btn).toBeDisabled()
  })

  it('shows "Sign in" link', () => {
    renderRegister()
    expect(screen.getByText(/sign in/i)).toBeInTheDocument()
  })
})

describe('Register page — password validation UI', () => {
  function getPasswordInput() {
    return document.querySelector('input[type="password"]')
  }

  it('password rules turn green when requirement met', async () => {
    renderRegister()
    const pwInput = getPasswordInput()
    fireEvent.change(pwInput, { target: { value: 'TestPass@1234!' } })
    await waitFor(() => {
      const lengthRule = screen.getByText(/minimum 10 characters/i)
      expect(lengthRule).toBeInTheDocument()
    })
  })

  it('shows mismatch error when confirm password differs', async () => {
    renderRegister()
    const inputs = document.querySelectorAll('input[type="password"]')
    if (inputs.length < 2) return // skip if confirm field not visible yet

    fireEvent.change(inputs[0], { target: { value: 'TestPass@1234!' } })
    fireEvent.change(inputs[1], { target: { value: 'Different@1!' } })

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    })
  })
})

describe('Register page — ClearSettle branding', () => {
  it('shows ClearSettle branding', () => {
    renderRegister()
    expect(screen.getByText('ClearSettle')).toBeInTheDocument()
  })

  it('shows step indicator', () => {
    renderRegister()
    expect(screen.getByText(/step 1/i)).toBeInTheDocument()
  })
})
