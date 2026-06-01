# Design Tokens
**Version:** 1.0 | **Owner:** `uiux-agent`

This is the canonical source of truth for all visual design values in ClearSettle. Every agent that produces visual output (web, mobile, future desktop) must consume these tokens. No hardcoded values in production code.

---

## Color Tokens

### Brand Colors
```
Navy (Background scale):
  --color-navy-900:  #061020   (darkest — auth screen bg end)
  --color-navy-800:  #0A1628   (auth screen bg mid)
  --color-navy-700:  #0D1F35   (auth screen bg start / primary text)
  --color-navy-600:  #162B48   (dark card bg)
  --color-navy-500:  #1A3A5C   (mobile primary)
  --color-navy-400:  #2E5F8A   (mobile primary light)

Teal (Primary Accent / CTA):
  --color-teal-700:  #088F99   (CTA gradient end / hover)
  --color-teal-500:  #0ABFCA   (primary CTA)
  --color-teal-300:  #7FE4EC   (gradient text light end)

Supporting:
  --color-purple:    #7B52E8   (decorative accent / orbs)
  --color-green:     #0DB07A   (success / positive financials)
  --color-amber:     #E9930D   (warning)
  --color-red:       #E8344A   (error / negative financials)
  --color-red-light: #F87171   (error text on dark bg)
  --color-blue:      #2563EB   (info / links)
```

### Marketplace Brand Colors
```
--color-flipkart:  #2874F0
--color-amazon:    #FF9900
--color-meesho:    #F43397
--color-myntra:    #FF3F6C
--color-ajio:      #E8234A
--color-jiomart:   #0067B2
```

### Text Colors
```
Light Theme:
  --color-text-primary:    #0D1F35  (headings, body)
  --color-text-secondary:  #4B6080  (subtitles, captions)
  --color-text-muted:      #8FA5BD  (field labels, placeholders)
  --color-text-disabled:   #B0BAC9
  --color-text-inverse:    #FFFFFF  (on dark bg)

Dark Theme (Auth screens):
  --color-text-dark-primary:    #FFFFFF
  --color-text-dark-secondary:  #4B6080
  --color-text-dark-muted:      #8FA5BD
```

### Surface Colors
```
Light Theme:
  --color-surface:    #FFFFFF
  --color-surface-2:  #F1F5F9
  --color-surface-3:  #E8F0F8
  --color-border:     #E2EBF3

Dark/Auth Theme:
  --color-auth-card:           rgba(255,255,255,0.05)
  --color-auth-card-border:    rgba(255,255,255,0.10)
  --color-auth-input:          rgba(255,255,255,0.07)
  --color-auth-input-border:   rgba(255,255,255,0.12)
  --color-auth-error-bg:       rgba(232,52,74,0.15)
  --color-auth-error-border:   rgba(232,52,74,0.30)
```

---

## Typography Tokens

### Font Families
```
Web:    'Plus Jakarta Sans', system-ui, -apple-system, sans-serif
Mobile: 'Inter' via google_fonts (fallback: Roboto)
Mono:   'JetBrains Mono', 'Fira Code', monospace
```

### Font Weight Scale
```
--font-regular:    400
--font-medium:     500
--font-semibold:   600
--font-bold:       700
--font-extrabold:  800
```

### Font Size Scale (Web — CSS)
```
--text-xs:   11px
--text-sm:   12px
--text-base: 14px
--text-md:   15px
--text-lg:   clamp(15px, 2vw, 18px)
--text-xl:   clamp(18px, 2.5vw, 22px)
--text-2xl:  clamp(20px, 3vw, 28px)
```

### Font Size Scale (Mobile — Flutter)
```
labelSmall:    11px / w500
labelMedium:   12px / w500
bodySmall:     12px / w400
labelLarge:    14px / w500
bodyMedium:    14px / w400
bodyLarge:     16px / w400
titleMedium:   14px / w500
titleLarge:    16px / w600
headlineMedium: 18px / w600
headlineLarge: 20px / w600
displayMedium: 24px / w700
displayLarge:  28px / w700
```

---

## Spacing Scale
```
--space-1:  4px    (micro — icon gaps)
--space-2:  8px    (small — field gaps)
--space-3:  12px   (medium-small)
--space-4:  16px   (standard — padding)
--space-5:  20px   (medium)
--space-6:  24px   (large — section gaps)
--space-7:  28px   (extra-large)
--space-8:  32px   (2x standard)
--space-10: 40px   (section separators)
--space-12: 48px   (page sections)
```

---

## Border Radius Scale
```
--radius-xs:  4px   (tags, badges)
--radius-sm:  6px   (small elements)
--radius-md:  9px   (buttons, inputs)
--radius-lg:  12px  (cards)
--radius-xl:  14px  (large cards)
--radius-2xl: 18px  (featured cards)
--radius-3xl: 24px  (modal sheets)
--radius-pill: 9999px (pills, chips)
```

---

## Shadow Scale
```
--shadow-1: 0 1px 3px rgba(13,31,53,.06)      (subtle lift)
--shadow-2: 0 4px 16px rgba(13,31,53,.08)     (card hover)
--shadow-3: 0 8px 32px rgba(13,31,53,.12)     (elevated card)
--shadow-4: 0 20px 60px rgba(13,31,53,.18)    (modal/drawer)
```

---

## Component Patterns

### Auth Screen Background
```
gradient: linear-gradient(135deg, #0D1F35 0%, #0A1628 50%, #061020 100%)
```

### Primary CTA Button
```
background: linear-gradient(135deg, #0ABFCA, #088F99)
shadow: 0 2px 8px rgba(10,191,202,0.25)
hover-shadow: 0 5px 16px rgba(10,191,202,0.35)
border-radius: var(--radius-md)
min-height: 44px (web) / 52px (mobile)
```

### Glassmorphism Card (Auth/Modal)
```
background: rgba(255,255,255,0.05)
backdrop-filter: blur(20px)
border: 1px solid rgba(255,255,255,0.10)
border-radius: var(--radius-3xl)
```

### Error Banner (Dark Theme)
```
background: rgba(232,52,74,0.15)
border: 1px solid rgba(232,52,74,0.30)
color: #F87171
border-radius: var(--radius-md)
```

### Positive Amount
```
color: #0DB07A (--color-green)
font-weight: 700
```

### Negative Amount
```
color: #E8344A (--color-red)
font-weight: 700
```

---

## Accessibility Minimums

| Element | Requirement |
|---|---|
| Normal text | 4.5:1 contrast ratio minimum |
| Large text (>18px or bold >14px) | 3:1 contrast ratio minimum |
| Interactive elements | 44×44px minimum touch target (mobile) |
| Form inputs | Visible label always |
| Buttons | Accessible name via text or aria-label |
| Images | Alt text required |
| Focus state | Visible `:focus-visible` outline |

---

## Version History
- v1.0 (2026-06-01): Initial canonical token set extracted from web app CSS and mobile app AppColors
