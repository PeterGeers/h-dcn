/**
 * WebAuthn Service for H-DCN Passkey Authentication
 * 
 * This service handles passkey registration and authentication using the WebAuthn API.
 * It integrates with AWS Cognito's passwordless authentication flow.
 */

export interface PasskeyRegistrationOptions {
  challenge: string;
  rp: {
    name: string;
    id: string;
  };
  user: {
    id: string;
    name: string;
    displayName: string;
  };
  pubKeyCredParams: Array<{
    type: 'public-key';
    alg: number;
  }>;
  authenticatorSelection?: {
    authenticatorAttachment?: 'platform' | 'cross-platform';
    userVerification?: 'required' | 'preferred' | 'discouraged';
    requireResidentKey?: boolean;
  };
  timeout?: number;
  attestation?: 'none' | 'indirect' | 'direct';
}

export interface PasskeyAuthenticationOptions {
  challenge: string;
  allowCredentials?: Array<{
    type: 'public-key';
    id: ArrayBuffer;
  }>;
  userVerification?: 'required' | 'preferred' | 'discouraged';
  timeout?: number;
}

export class WebAuthnService {
  /**
   * Check if WebAuthn is supported in the current browser
   */
  static isSupported(): boolean {
    return !!(
      window.PublicKeyCredential &&
      navigator.credentials &&
      navigator.credentials.create &&
      navigator.credentials.get
    );
  }

  /**
   * Check if platform authenticator (built-in biometrics) is available
   */
  static async isPlatformAuthenticatorAvailable(): Promise<boolean> {
    if (!this.isSupported()) {
      return false;
    }

    try {
      return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    } catch (error) {
      console.warn('Error checking platform authenticator availability:', error);
      return false;
    }
  }

  /**
   * Check if this is a mobile device
   */
  static isMobileDevice(): boolean {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  /**
   * Get recommended authenticator attachment for this device
   */
  static getRecommendedAuthenticatorAttachment(): 'platform' | 'cross-platform' | undefined {
    if (this.isMobileDevice()) {
      // Mobile devices typically have platform authenticators (biometrics)
      return 'platform';
    } else {
      // Desktop can use either, but prefer platform if available
      return 'platform';
    }
  }

  /**
   * Check if cross-device authentication should be offered
   */
  static shouldOfferCrossDeviceAuth(): boolean {
    // Offer cross-device auth on desktop or when platform authenticator is not available
    return !this.isMobileDevice();
  }

  /**
   * Create authentication options for cross-device authentication
   */
  static createCrossDeviceAuthOptions(challenge: string): PasskeyAuthenticationOptions {
    return {
      challenge,
      // Empty allowCredentials enables cross-device authentication
      allowCredentials: [],
      userVerification: 'preferred',
      timeout: 300000, // 5 minutes for cross-device auth
    };
  }

  /**
   * Get browser and platform information for debugging
   */
  static getBrowserInfo(): {
    userAgent: string;
    webAuthnSupported: boolean;
    platformAuthenticator: boolean;
    isMobile: boolean;
    recommendedAttachment: 'platform' | 'cross-platform' | undefined;
    supportsCrossDevice: boolean;
  } {
    return {
      userAgent: navigator.userAgent,
      webAuthnSupported: this.isSupported(),
      platformAuthenticator: false, // Will be set asynchronously
      isMobile: this.isMobileDevice(),
      recommendedAttachment: this.getRecommendedAuthenticatorAttachment(),
      supportsCrossDevice: this.shouldOfferCrossDeviceAuth()
    };
  }

  /**
   * Register a new passkey for the user
   */
  static async registerPasskey(options: PasskeyRegistrationOptions): Promise<PublicKeyCredential> {
    if (!this.isSupported()) {
      throw new Error('WebAuthn is not supported in this browser');
    }

    try {
      // Convert base64url strings to ArrayBuffers
      const publicKeyCredentialCreationOptions: PublicKeyCredentialCreationOptions = {
        challenge: this.base64urlToArrayBuffer(options.challenge),
        rp: options.rp,
        user: {
          id: this.stringToArrayBuffer(options.user.id),
          name: options.user.name,
          displayName: options.user.displayName,
        },
        pubKeyCredParams: options.pubKeyCredParams,
        authenticatorSelection: options.authenticatorSelection || {
          authenticatorAttachment: this.getRecommendedAuthenticatorAttachment(),
          userVerification: 'preferred',
          requireResidentKey: false,
        },
        timeout: options.timeout || 60000,
        attestation: options.attestation || 'none',
      };

      const credential = await navigator.credentials.create({
        publicKey: publicKeyCredentialCreationOptions,
      });

      if (!credential || credential.type !== 'public-key') {
        throw new Error('Failed to create passkey credential');
      }

      return credential as PublicKeyCredential;
    } catch (error) {
      console.error('Passkey registration failed:', error);
      throw this.handleWebAuthnError(error);
    }
  }

  /**
   * Authenticate using an existing passkey
   */
  static async authenticateWithPasskey(options: PasskeyAuthenticationOptions): Promise<PublicKeyCredential> {
    if (!this.isSupported()) {
      throw new Error('WebAuthn is not supported in this browser');
    }

    try {
      const publicKeyCredentialRequestOptions: PublicKeyCredentialRequestOptions = {
        challenge: this.base64urlToArrayBuffer(options.challenge),
        allowCredentials: options.allowCredentials?.map(cred => ({
          type: cred.type,
          id: cred.id,
        })),
        userVerification: options.userVerification || 'preferred',
        timeout: options.timeout || 60000,
      };

      const credential = await navigator.credentials.get({
        publicKey: publicKeyCredentialRequestOptions,
      });

      if (!credential || credential.type !== 'public-key') {
        throw new Error('Failed to authenticate with passkey');
      }

      return credential as PublicKeyCredential;
    } catch (error) {
      console.error('Passkey authentication failed:', error);
      throw this.handleWebAuthnError(error);
    }
  }

  /**
   * Convert a PublicKeyCredential to a format suitable for sending to the server
   */
  static credentialToJSON(credential: PublicKeyCredential): any {
    const response = credential.response;
    
    if (response instanceof AuthenticatorAttestationResponse) {
      // Registration response
      return {
        id: credential.id,
        rawId: this.arrayBufferToBase64url(credential.rawId),
        type: credential.type,
        response: {
          attestationObject: this.arrayBufferToBase64url(response.attestationObject),
          clientDataJSON: this.arrayBufferToBase64url(response.clientDataJSON),
        },
      };
    } else if (response instanceof AuthenticatorAssertionResponse) {
      // Authentication response
      return {
        id: credential.id,
        rawId: this.arrayBufferToBase64url(credential.rawId),
        type: credential.type,
        response: {
          authenticatorData: this.arrayBufferToBase64url(response.authenticatorData),
          clientDataJSON: this.arrayBufferToBase64url(response.clientDataJSON),
          signature: this.arrayBufferToBase64url(response.signature),
          userHandle: response.userHandle ? this.arrayBufferToBase64url(response.userHandle) : null,
        },
      };
    }

    throw new Error('Unknown credential response type');
  }

  /**
   * Convert base64url string to ArrayBuffer
   */
  private static base64urlToArrayBuffer(base64url: string): ArrayBuffer {
    // Add padding if needed
    const padding = '='.repeat((4 - (base64url.length % 4)) % 4);
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + padding;
    
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    return bytes.buffer;
  }

  /**
   * Convert ArrayBuffer to base64url string
   */
  private static arrayBufferToBase64url(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binaryString = '';
    
    for (let i = 0; i < bytes.length; i++) {
      binaryString += String.fromCharCode(bytes[i]);
    }
    
    const base64 = btoa(binaryString);
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }

  /**
   * Convert string to ArrayBuffer
   */
  private static stringToArrayBuffer(str: string): ArrayBuffer {
    const encoder = new TextEncoder();
    return encoder.encode(str).buffer;
  }

  /**
   * Handle WebAuthn errors and provide user-friendly messages
   */
  private static handleWebAuthnError(error: any): Error {
    if (error.name === 'NotSupportedError') {
      return new Error('Passkeys zijn niet ondersteund op dit apparaat of in deze browser');
    }
    
    if (error.name === 'SecurityError') {
      return new Error('Beveiligingsfout: Passkey registratie geblokkeerd');
    }
    
    if (error.name === 'NotAllowedError') {
      return new Error('Passkey registratie geannuleerd door gebruiker');
    }
    
    if (error.name === 'InvalidStateError') {
      return new Error('Er bestaat al een passkey voor dit account op dit apparaat');
    }
    
    if (error.name === 'ConstraintError') {
      return new Error('Passkey vereisten niet ondersteund door dit apparaat');
    }
    
    if (error.name === 'UnknownError') {
      return new Error('Onbekende fout bij passkey registratie');
    }

    // Return original error if we don't have a specific translation
    return error instanceof Error ? error : new Error('Passkey operatie mislukt');
  }
}