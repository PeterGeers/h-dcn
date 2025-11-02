import { extendTheme, type ThemeConfig } from '@chakra-ui/react';

const theme = extendTheme({
  breakpoints: {
    base: '0px',
    sm: '480px',
    md: '768px',
    lg: '992px',
    xl: '1280px',
    '2xl': '1536px',
  },
  styles: {
    global: {
      body: {
        bg: '#0f0f0f',
        color: '#f2f2f2',
        // Mobile optimizations
        overflowX: 'hidden',
      },
      // Ensure proper sizing on mobile
      '*': {
        boxSizing: 'border-box',
      },
    },
  },
  colors: {
    brand: {
      orange: '#ff6600',
      gray: '#1a1a1a',
    },
  },
  components: {
    Button: {
      baseStyle: {
        // Ensure buttons are touch-friendly on mobile
        minH: { base: '44px', md: 'auto' },
      },
    },
  },
});

export default theme;