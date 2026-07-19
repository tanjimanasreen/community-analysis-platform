import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('react-force-graph') || id.includes('three')) return 'graph-vendor'
          if (id.includes('recharts') || id.includes('d3-')) return 'chart-vendor'
          if (id.includes('@tanstack/react-query') || id.includes('axios')) return 'data-vendor'
          if (id.includes('react-router') || id.includes('react-dom') || id.includes('/react/')) return 'react-vendor'
          return undefined
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{js,jsx,ts,tsx}'],
    clearMocks: true,
    restoreMocks: true,
    mockReset: true,
    pool: 'forks',
    poolOptions: { forks: { singleFork: true } },
    fileParallelism: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: [
        'src/api/errors.ts',
        'src/api/routes.ts',
        'src/app/dashboardSearchParams.ts',
        'src/features/**/*Model.ts',
        'src/features/**/overviewUtils.ts',
        'src/features/**/communityUtils.ts',
        'src/features/**/artifactLibrary.ts',
        'src/features/**/runCompatibility.ts',
        'src/utils/*.ts',
      ],
      exclude: ['src/**/*.test.*', 'src/**/__tests__/**'],
      thresholds: {
        statements: 70,
        branches: 60,
        functions: 70,
        lines: 70,
      },
    },
  },
})
