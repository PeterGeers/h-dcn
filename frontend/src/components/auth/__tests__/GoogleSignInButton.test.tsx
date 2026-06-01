import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

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
