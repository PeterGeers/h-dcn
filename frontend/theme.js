import { extendTheme } from '@chakra-ui/react';

const theme = extendTheme({
  styles: {
    global: {
      body: {
        bg: '#0f0f0f',
        color: '#f2f2f2',
      },
    },
  },
  colors: {
    brand: {
      orange: '#ff6600',
      gray: '#1a1a1a',
    },
  },
});

export default theme;