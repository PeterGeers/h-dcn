/**
 * Jest configuration specifically for DataProcessingService testing
 * This provides focused testing with performance monitoring and detailed reporting
 */

const { defaults } = require('jest-config');

module.exports = {
  // Extend the default Create React App Jest configuration
  ...defaults,
  
  // Test environment
  testEnvironment: 'jsdom',
  
  // Setup files
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  
  // Test file patterns - focus on DataProcessingService
  testMatch: [
    '<rootDir>/src/services/__tests__/DataProcessingService.test.ts',
    '<rootDir>/src/services/__tests__/DataProcessingService.*.test.ts'
  ],
  
  // Coverage configuration
  collectCoverage: true,
  collectCoverageFrom: [
    'src/services/DataProcessingService.ts',
    'src/services/DataProcessingService.*.ts'
  ],
  coverageDirectory: 'coverage/data-processing',
  coverageReporters: [
    'text',
    'text-summary',
    'html',
    'lcov',
    'json'
  ],
  coverageThreshold: {
    global: {
      branches: 90,
      functions: 95,
      lines: 95,
      statements: 95
    },
    './src/services/DataProcessingService.ts': {
      branches: 95,
      functions: 100,
      lines: 98,
      statements: 98
    }
  },
  
  // Performance monitoring
  verbose: true,
  detectOpenHandles: true,
  forceExit: true,
  
  // Module resolution
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  
  // Transform configuration
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
    '^.+\\.(js|jsx)$': 'babel-jest'
  },
  
  // File extensions to consider
  moduleFileExtensions: [
    'ts',
    'tsx',
    'js',
    'jsx',
    'json'
  ],
  
  // Test timeout (important for performance tests)
  testTimeout: 10000,
  
  // Reporter configuration for detailed output
  reporters: [
    'default',
    [
      'jest-html-reporters',
      {
        publicPath: './coverage/data-processing/html-report',
        filename: 'report.html',
        expand: true,
        hideIcon: false,
        pageTitle: 'DataProcessingService Test Report'
      }
    ]
  ],
  
  // Global test setup
  globals: {
    'ts-jest': {
      tsconfig: 'tsconfig.json'
    }
  }
};