import React from 'react'

var inputStyle = {
  padding: '11px 14px', borderRadius: 10,
  background: 'rgba(255,255,255,.07)',
  border: '1px solid rgba(255,255,255,.13)',
  color: '#fff', fontSize: 14, outline: 'none', width: '100%',
  boxSizing: 'border-box',
}
var labelStyle = { fontSize: 12, fontWeight: 600, color: '#8FA5BD', marginBottom: 5, display: 'block' }
var fieldWrap = { display: 'flex', flexDirection: 'column', marginBottom: 16 }

function EyeIcon({ open }) {
  return open ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <path d="M14.12 14.12a3 3 0 0 1-4.24-4.24"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  )
}

/**
 * Accessible password input with eye-toggle.
 *
 * Props:
 *   id              — links <label htmlFor> to <input id>
 *   label           — visible label text (e.g. "Password *")
 *   value / onChange — controlled
 *   placeholder     — input placeholder
 *   show            — whether password is visible
 *   onToggleShow    — callback to flip show
 *   ariaDescribedBy — id of element describing constraints (e.g. checklist)
 *   ariaInvalid     — true when field has a validation error
 */
function PasswordInput({
  id,
  label,
  value,
  onChange,
  placeholder,
  show,
  onToggleShow,
  ariaDescribedBy,
  ariaInvalid,
}) {
  return (
    <div style={fieldWrap}>
      <label htmlFor={id} style={labelStyle}>{label}</label>
      <div style={{ position: 'relative' }}>
        <input
          id={id}
          style={{ ...inputStyle, paddingRight: 44 }}
          type={show ? 'text' : 'password'}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          autoComplete="new-password"
          aria-describedby={ariaDescribedBy || undefined}
          aria-invalid={ariaInvalid || undefined}
        />
        <button
          type="button"
          onClick={onToggleShow}
          aria-label={show ? 'Hide password' : 'Show password'}
          style={{
            position: 'absolute', right: 12, top: '50%',
            transform: 'translateY(-50%)',
            background: 'none', border: 'none', padding: 4,
            cursor: 'pointer', color: '#4B6080',
            display: 'flex', alignItems: 'center', transition: 'color .15s',
          }}
          onMouseEnter={function(e) { e.currentTarget.style.color = '#8FA5BD' }}
          onMouseLeave={function(e) { e.currentTarget.style.color = '#4B6080' }}
        >
          <EyeIcon open={show} />
        </button>
      </div>
    </div>
  )
}

export default PasswordInput
