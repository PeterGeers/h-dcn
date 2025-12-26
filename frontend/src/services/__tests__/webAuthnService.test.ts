import { WebAuthnService } from '../webAuthnService';

// Mock WebAuthn API classes
class MockAuthenticatorAttestationResponse {
  attestationObject: ArrayBuffer;
  clientDataJSON: ArrayBuffer;

  constructor(attestationObject: ArrayBuffer, clientDataJSON: ArrayBuffer) {
    this.attestationObject = attestationObject;
    this.clientDataJSON = clientDataJSON;
  }
}

class MockAuthenticatorAssertionResponse {
  authenticatorData: ArrayBuffer;
  clientDataJSON: ArrayBuffer;
  signature: ArrayBuffer;
  userHandle: ArrayBuffer | null;

  constructor(
    authenticatorData: ArrayBuffer,
    clientDataJSON: ArrayBuffer,
    signature: ArrayBuffer,
    userHandle: ArrayBuffer | null = null
  ) {
    this.authenticatorData = authenticatorData;
    this.clientDataJSON = clientDataJSON;
    this.signature = signature;
    this.userHandle = userHandle;
  }
}

// Add to global scope
(global as any).AuthenticatorAttestationResponse = MockAuthenticatorAttestationResponse;
(global as any).AuthenticatorAssertionResponse = MockAuthenticatorAssertionResponse;

// Mock WebAuthn API
const mockCredentialsCreate = jest.fn();
const mockCredentialsGet = jest.fn();
const mockIsUserVerifyingPlatformAuthenticatorAvailable = jest.fn();

Object.defineProperty(global, 'PublicKeyCredential', {
  value: {
    isUserVerifyingPlatformAuthenticatorAvailable: mockIsUserVerifyingPlatformAuthenticatorAvailable,
  },
  writable: true,
});

Object.defineProperty(global.navigator, 'credentials', {
  value: {
    create: mockCredentialsCreate,
    get: mockCredentialsGet,
  },
  writable: true,
});

// Mock TextEncoder for string to ArrayBuffer conversion
Object.defineProperty(global, 'TextEncoder', {
  value: class TextEncoder {
    encode(str: string) {
      return new Uint8Array(Buffer.from(str, 'utf8'));
    }
  },
  writable: true,
});

// Mock atob and btoa for base64 operations
Object.defineProperty(global, 'atob', {
  value: (str: string) => Buffer.from(str, 'base64').toString('binary'),
  writable: true,
});

Object.defineProperty(global, 'btoa', {
  value: (str: string) => Buffer.from(str, 'binary').toString('base64'),
  writable: true,
});

describe('WebAuthnService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Browser Support Detection', () => {
    test('detects WebAuthn support correctly', () => {
      expect(WebAuthnService.isSupported()).toBe(true);
    });

    test('detects when WebAuthn is not supported', () => {
      // Since we can't easily mock navigator.credentials in Jest,
      // let's test a different scenario - when window.PublicKeyCredential exists
      // but navigator.credentials doesn't have the required methods
      const originalPublicKeyCredential = global.PublicKeyCredential;
      const originalCreate = global.navigator.credentials.create;
      const originalGet = global.navigator.credentials.get;
      
      // Remove the create and get methods to simulate lack of support
      delete (global.navigator.credentials as any).create;
      delete (global.navigator.credentials as any).get;

      expect(WebAuthnService.isSupported()).toBe(false);

      // Restore WebAuthn support
      (global.navigator.credentials as any).create = originalCreate;
      (global.navigator.credentials as any).get = originalGet;
    });

    test('checks platform authenticator availability', async () => {
      mockIsUserVerifyingPlatformAuthenticatorAvailable.mockResolvedValue(true);

      const isAvailable = await WebAuthnService.isPlatformAuthenticatorAvailable();
      expect(isAvailable).toBe(true);
      expect(mockIsUserVerifyingPlatformAuthenticatorAvailable).toHaveBeenCalled();
    });

    test('handles platform authenticator check errors', async () => {
      mockIsUserVerifyingPlatformAuthenticatorAvailable.mockRejectedValue(new Error('Not available'));

      const isAvailable = await WebAuthnService.isPlatformAuthenticatorAvailable();
      expect(isAvailable).toBe(false);
    });

    test('detects mobile devices correctly', () => {
      // Mock mobile user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
        writable: true,
      });

      expect(WebAuthnService.isMobileDevice()).toBe(true);

      // Mock desktop user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        writable: true,
      });

      expect(WebAuthnService.isMobileDevice()).toBe(false);
    });

    test('provides correct authenticator attachment recommendations', () => {
      // Mock mobile user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
        writable: true,
      });

      expect(WebAuthnService.getRecommendedAuthenticatorAttachment()).toBe('platform');

      // Mock desktop user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        writable: true,
      });

      expect(WebAuthnService.getRecommendedAuthenticatorAttachment()).toBe('platform');
    });

    test('determines when to offer cross-device auth', () => {
      // Mock mobile user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
        writable: true,
      });

      expect(WebAuthnService.shouldOfferCrossDeviceAuth()).toBe(false);

      // Mock desktop user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        writable: true,
      });

      expect(WebAuthnService.shouldOfferCrossDeviceAuth()).toBe(true);
    });
  });

  describe('Passkey Registration', () => {
    test('successfully registers a passkey', async () => {
      const mockCredential = {
        id: 'test-credential-id',
        type: 'public-key',
        rawId: new ArrayBuffer(16),
        response: {
          attestationObject: new ArrayBuffer(32),
          clientDataJSON: new ArrayBuffer(64),
        },
      };

      mockCredentialsCreate.mockResolvedValue(mockCredential);

      const options = {
        challenge: 'dGVzdC1jaGFsbGVuZ2U', // base64url encoded "test-challenge"
        rp: {
          name: 'H-DCN Portal',
          id: 'localhost',
        },
        user: {
          id: 'test@example.com',
          name: 'test@example.com',
          displayName: 'test@example.com',
        },
        pubKeyCredParams: [
          { type: 'public-key' as const, alg: -7 },
          { type: 'public-key' as const, alg: -257 },
        ],
      };

      const result = await WebAuthnService.registerPasskey(options);
      expect(result).toBe(mockCredential);
      expect(mockCredentialsCreate).toHaveBeenCalled();
    });

    test('handles registration errors', async () => {
      mockCredentialsCreate.mockRejectedValue(new Error('Registration failed'));

      const options = {
        challenge: 'dGVzdC1jaGFsbGVuZ2U',
        rp: { name: 'H-DCN Portal', id: 'localhost' },
        user: { id: 'test@example.com', name: 'test@example.com', displayName: 'test@example.com' },
        pubKeyCredParams: [{ type: 'public-key' as const, alg: -7 }],
      };

      await expect(WebAuthnService.registerPasskey(options)).rejects.toThrow();
    });

    test('handles specific WebAuthn errors with user-friendly messages', async () => {
      const notSupportedError = new Error('Not supported');
      notSupportedError.name = 'NotSupportedError';
      mockCredentialsCreate.mockRejectedValue(notSupportedError);

      const options = {
        challenge: 'dGVzdC1jaGFsbGVuZ2U',
        rp: { name: 'H-DCN Portal', id: 'localhost' },
        user: { id: 'test@example.com', name: 'test@example.com', displayName: 'test@example.com' },
        pubKeyCredParams: [{ type: 'public-key' as const, alg: -7 }],
      };

      await expect(WebAuthnService.registerPasskey(options)).rejects.toThrow(
        'Passkeys zijn niet ondersteund op dit apparaat of in deze browser'
      );
    });
  });

  describe('Passkey Authentication', () => {
    test('successfully authenticates with passkey', async () => {
      const mockCredential = {
        id: 'test-credential-id',
        type: 'public-key',
        rawId: new ArrayBuffer(16),
        response: {
          authenticatorData: new ArrayBuffer(32),
          clientDataJSON: new ArrayBuffer(64),
          signature: new ArrayBuffer(32),
          userHandle: new ArrayBuffer(8),
        },
      };

      mockCredentialsGet.mockResolvedValue(mockCredential);

      const options = {
        challenge: 'dGVzdC1jaGFsbGVuZ2U',
        allowCredentials: [],
        userVerification: 'preferred' as const,
      };

      const result = await WebAuthnService.authenticateWithPasskey(options);
      expect(result).toBe(mockCredential);
      expect(mockCredentialsGet).toHaveBeenCalled();
    });

    test('handles authentication errors', async () => {
      mockCredentialsGet.mockRejectedValue(new Error('Authentication failed'));

      const options = {
        challenge: 'dGVzdC1jaGFsbGVuZ2U',
        allowCredentials: [],
      };

      await expect(WebAuthnService.authenticateWithPasskey(options)).rejects.toThrow();
    });
  });

  describe('Credential Conversion', () => {
    test('converts registration credential to JSON', () => {
      const mockCredential = {
        id: 'test-credential-id',
        rawId: new ArrayBuffer(16),
        type: 'public-key',
        response: new MockAuthenticatorAttestationResponse(
          new ArrayBuffer(32),
          new ArrayBuffer(64)
        ),
      };

      const result = WebAuthnService.credentialToJSON(mockCredential as any);

      expect(result).toHaveProperty('id', 'test-credential-id');
      expect(result).toHaveProperty('type', 'public-key');
      expect(result).toHaveProperty('response.attestationObject');
      expect(result).toHaveProperty('response.clientDataJSON');
    });

    test('converts authentication credential to JSON', () => {
      const mockCredential = {
        id: 'test-credential-id',
        rawId: new ArrayBuffer(16),
        type: 'public-key',
        response: new MockAuthenticatorAssertionResponse(
          new ArrayBuffer(32),
          new ArrayBuffer(64),
          new ArrayBuffer(32),
          new ArrayBuffer(8)
        ),
      };

      const result = WebAuthnService.credentialToJSON(mockCredential as any);

      expect(result).toHaveProperty('id', 'test-credential-id');
      expect(result).toHaveProperty('type', 'public-key');
      expect(result).toHaveProperty('response.authenticatorData');
      expect(result).toHaveProperty('response.clientDataJSON');
      expect(result).toHaveProperty('response.signature');
      expect(result).toHaveProperty('response.userHandle');
    });
  });

  describe('Cross-Device Authentication', () => {
    test('creates correct cross-device auth options', () => {
      const challenge = 'test-challenge';
      const options = WebAuthnService.createCrossDeviceAuthOptions(challenge);

      expect(options).toEqual({
        challenge: 'test-challenge',
        allowCredentials: [],
        userVerification: 'preferred',
        timeout: 300000,
      });
    });
  });

  describe('Browser Information', () => {
    test('returns comprehensive browser information', () => {
      const info = WebAuthnService.getBrowserInfo();

      expect(info).toHaveProperty('userAgent');
      expect(info).toHaveProperty('webAuthnSupported');
      expect(info).toHaveProperty('platformAuthenticator');
      expect(info).toHaveProperty('isMobile');
      expect(info).toHaveProperty('recommendedAttachment');
      expect(info).toHaveProperty('supportsCrossDevice');
    });
  });
});