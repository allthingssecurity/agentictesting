import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    // Include tests in both tests/ and __tests__/, supporting js/ts and test/spec naming
    include: [
      'tests/**/*.{test,spec}.{ts,tsx,js,jsx}',
      '**/__tests__/**/*.{test,spec}.{ts,tsx,js,jsx}',
    ],
  },
})
