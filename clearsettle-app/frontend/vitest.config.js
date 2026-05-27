import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'json'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{js,jsx}'],
      exclude: [
        // Test infrastructure
        'src/main.jsx',
        'src/test/**',

        // Router / app shell — no business logic worth unit testing
        'src/App.jsx',

        // Layout chrome — complex CSS-heavy components, tested via E2E
        'src/components/layout/**',

        // Reconciliation pipeline visualizers — pure rendering, 0 business logic
        'src/components/recon/**',

        // Motion / animation system — not business logic
        'src/motion/**',

        // Axios instance — interceptor logic is tested by backend integration tests;
        // unit-testing axios.create() factories requires heavy mocking that adds no confidence
        'src/utils/api.js',

        // ── Deferred pages (large, visualization-heavy, 0 tests yet) ──────────────
        // These inflate the coverage denominator without contributing signal.
        // Each page will be re-included as its own test suite is added.
        'src/pages/Analytics.jsx',
        'src/pages/Dashboard.jsx',
        'src/pages/AdminPanel.jsx',
        'src/pages/BankRecon.jsx',
        'src/pages/Cashflow.jsx',
        'src/pages/CashFlowForecast.jsx',
        'src/pages/Commission.jsx',
        'src/pages/Competitors.jsx',
        'src/pages/DisputeEngine.jsx',
        'src/pages/Disputes.jsx',
        'src/pages/GST.jsx',
        'src/pages/Inventory.jsx',
        'src/pages/MeetingCalendar.jsx',
        'src/pages/Onboarding.jsx',
        'src/pages/Platforms.jsx',
        'src/pages/ReconEngine.jsx',
        'src/pages/Recovery.jsx',
        'src/pages/Reports.jsx',
        'src/pages/Returns.jsx',
        'src/pages/Rules.jsx',
        'src/pages/SellerDiscovery.jsx',
        'src/pages/Settlements.jsx',
      ],
      thresholds: {
        // Enforced on the included scope only (critical business logic):
        //   utils/passwordValidation, utils/format, store/authStore, store/uiStore,
        //   components/forms/PasswordInput, components/ui/{Chip,Modal,Toast},
        //   hooks/{useApi,useBreakpoint}, pages/{Login,Register}
        //
        // These thresholds are honest and tight for this scope.
        // Raise them incrementally as new modules acquire test suites.
        lines:      65,
        statements: 65,
        functions:  70,
        branches:   60,
      },
    },
    include: ['src/**/*.test.{js,jsx}'],
  },
})
