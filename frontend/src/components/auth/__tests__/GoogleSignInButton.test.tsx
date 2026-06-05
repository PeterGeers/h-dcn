import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'login.google_button': 'Inloggen met Google',
      };
      return translations[key] || key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// Mock aws-amplify/auth
const mockSignInWithRedirect = jest.fn();
jest.mock('aws-amplify/auth', () => ({
  signInWithRedirect: (...args) => mockSignInWithRedirect(...args),
}));

import GoogleSignInButton from '../GoogleSignInButton';

describe('GoogleSignInButton', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignInWithRedirect.mockResolvedValue(undefined);
  });

  test('clicking button calls signInWithRedirect with { provider: "Google" }', async () => {
    render(<GoogleSignInButton />);

    const button = screen.getByRole('button', { name: /inloggen met google/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockSignInWithRedirect).toHaveBeenCalledTimes(1);
      expect(mockSignInWithRedirect).toHaveBeenCalledWith({ provider: 'Google' });
    });
  });

  test('calls onError when signInWithRedirect throws', async () => {
    const mockError = new Error('Network error');
    mockSignInWithRedirect.mockRejectedValue(mockError);
    const onError = jest.fn();

    render(<GoogleSignInButton onError={onError} />);

    const button = screen.getByRole('button', { name: /inloggen met google/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Network error');
    });
  });

  test('button is disabled when disabled prop is true', () => {
    render(<GoogleSignInButton disabled={true} />);

    const button = screen.getByRole('button', { name: /inloggen met google/i });
    expect(button).toBeDisabled();
  });
});
