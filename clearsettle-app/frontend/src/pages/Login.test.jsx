import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../utils/api', () => ({
  default: {
    post: vi.fn(),
  },
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

import api from '../utils/api'
import Login from './Login'

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Login page', () => {
  it('renders email and password fields', () => {
    renderLogin()
    expect(screen.getByPlaceholderText('you@company.in')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
  })

  it('renders Sign In button', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('renders ClearSettle branding', () => {
    renderLogin()
    expect(screen.getByText('ClearSettle')).toBeInTheDocument()
  })

  it('renders forgot password link', () => {
    renderLogin()
    expect(screen.getByText('Forgot password?')).toBeInTheDocument()
  })

  it('renders create account link', () => {
    renderLogin()
    expect(screen.getByText('Create a free account')).toBeInTheDocument()
  })

  it('shows loading state on submit', async () => {
    api.post.mockReturnValue(new Promise(() => {}))
    renderLogin()
    fireEvent.change(screen.getByPlaceholderText('you@company.in'), {
      target: { value: 'user@test.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'pass' },
    })
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }).closest('form'))
    await waitFor(() => {
      expect(screen.getByText('Signing in...')).toBeInTheDocument()
    })
  })

  it('shows error message on failed login', async () => {
    api.post.mockRejectedValue({
      response: { data: { detail: 'Invalid credentials' } },
    })
    renderLogin()
    fireEvent.change(screen.getByPlaceholderText('you@company.in'), {
      target: { value: 'user@test.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'wrongpass' },
    })
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }).closest('form'))
    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  it('shows fallback error when no detail in response', async () => {
    api.post.mockRejectedValue(new Error('Network error'))
    renderLogin()
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }).closest('form'))
    await waitFor(() => {
      expect(screen.getByText(/login failed/i)).toBeInTheDocument()
    })
  })

  it('updates email field on change', () => {
    renderLogin()
    const input = screen.getByPlaceholderText('you@company.in')
    fireEvent.change(input, { target: { value: 'new@email.com' } })
    expect(input.value).toBe('new@email.com')
  })

  it('updates password field on change', () => {
    renderLogin()
    const input = screen.getByPlaceholderText('••••••••')
    fireEvent.change(input, { target: { value: 'mypassword' } })
    expect(input.value).toBe('mypassword')
  })

  it('renders all feature items', () => {
    renderLogin()
    expect(screen.getByText(/dispute engine/i)).toBeInTheDocument()
    expect(screen.getByText(/bank reconciliation/i)).toBeInTheDocument()
  })
})
