# Passkey Authentication Implementation Guide

## Overview

This guide documents the implementation of passkey (WebAuthn) authentication in the H-DCN Portal. The system provides passwordless authentication using biometric authentication, security keys, and platform authenticators across desktop and mobile devices.

## Architecture

### WebAuthn Configuration

- **Relying Party ID**: `h-dcn.nl`
- **Relying Party Name**: "H-DCN Portal"
- **User Verification**: Required
- **Attestation**: None (for broader compatibility)
- **Timeout**: 60 seconds (desktop), 300 seconds (mobile)

### Supported Authenticators

- ✅ **Platform Authenticators**: Face ID, Touch ID, Windows Hello, Android Biometrics
- ✅ **Cross-Platform Authenticators**: USB security keys, Bluetooth keys
- ✅ **Mobile Devices**: iOS Safari, Android Chrome, Samsung Internet
- ✅ **Desktop Browsers**: Chrome, Firefox, Safari, Edge

## Implementation Components

### Frontend Service Layer

**File**: `frontend/src/services/webAuthnService.ts`

```typescript
class WebAuthnService {
  private rpId = "h-dcn.nl";
  private rpName = "H-DCN Portal";

  // Registration flow
  async registerPasskey(email: string): Promise<RegistrationResult>;

  // Authentication flow
  async authenticateWithPasskey(email: string): Promise<AuthenticationResult>;

  // Cross-device support
  async authenticateCrossDevice(email: string): Promise<AuthenticationResult>;
}
```

### Key Features

#### 1. **Mobile Device Detection**

```typescript
isMobileDevice(): boolean {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i
    .test(navigator.userAgent);
}
```

#### 2. **ArrayBuffer Conversion**

Critical for mobile compatibility:

```typescript
base64urlToArrayBuffer(base64url: string): ArrayBuffer {
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64.padEnd(base64.length + (4 - base64.length % 4) % 4, '=');
  const binary = atob(padded);
  const buffer = new ArrayBuffer(binary.length);
  const view = new Uint8Array(buffer);

  for (let i = 0; i < binary.length; i++) {
    view[i] = binary.charCodeAt(i);
  }

  return buffer;
}
```

#### 3. **Cross-Device Authentication**

For devices without WebAuthn support:

```typescript
async authenticateCrossDevice(email: string): Promise<AuthenticationResult> {
  // Generate QR code for cross-device authentication
  // Fallback to email verification
  // Guide user through alternative authentication
}
```

### Backend Integration

**File**: `backend/handler/hdcn_cognito_admin/app.py`

#### Credential Storage

```python
# Store passkey credentials in Cognito custom attributes
def store_passkey_credential(user_pool_id: str, username: str, credential_id: str):
    cognito_client.admin_update_user_attributes(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {
                'Name': 'custom:passkey_cred_ids',
                'Value': credential_id
            }
        ]
    )
```

#### Credential Verification

```python
def verify_passkey_authentication(challenge_response: dict) -> bool:
    # Verify WebAuthn assertion
    # Check credential against stored public key
    # Validate challenge and origin
    return verification_result
```

## User Experience Flow

### Registration Process

1. **Email Verification**

   - User enters email address
   - System sends verification code
   - User confirms email ownership

2. **Passkey Setup**

   - System prompts for passkey creation
   - Browser shows biometric/PIN prompt
   - User completes biometric authentication
   - Credential stored in Cognito

3. **Account Activation**
   - User assigned appropriate roles
   - Account marked as active
   - Welcome email sent

### Authentication Process

1. **Email Entry**

   - User enters email address
   - System checks for existing passkeys

2. **Biometric Prompt**

   - Browser shows authentication prompt
   - User completes biometric verification
   - System validates credential

3. **Session Creation**
   - JWT tokens generated
   - User roles loaded
   - Redirect to dashboard

### Cross-Device Flow

1. **Device Detection**

   - System detects mobile device
   - Checks WebAuthn support

2. **Alternative Authentication**
   - QR code generation (future)
   - Email verification fallback
   - SMS backup (if configured)

## Mobile Optimizations

### Timeout Configuration

```typescript
const getTimeout = (): number => {
  if (this.isMobileDevice()) {
    return 300000; // 5 minutes for mobile biometric prompts
  }
  return 60000; // 1 minute for desktop
};
```

### Error Handling

Mobile-specific error messages in Dutch:

```typescript
const getMobileErrorMessage = (error: WebAuthnError): string => {
  switch (error.name) {
    case "NotAllowedError":
      return "Gebruik je vingerafdruk, gezichtsherkenning, of apparaat-PIN om in te loggen.";
    case "TimeoutError":
      return "Probeer opnieuw en reageer sneller op de biometrische prompt.";
    case "NotSupportedError":
      return "Je apparaat ondersteunt geen biometrische authenticatie. Gebruik email verificatie.";
    default:
      return "Er ging iets mis met de biometrische authenticatie. Probeer het opnieuw.";
  }
};
```

### Browser Compatibility

```typescript
const checkWebAuthnSupport = (): boolean => {
  if (!window.PublicKeyCredential) {
    return false;
  }

  // Check for platform authenticator support
  return PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
};
```

## Security Implementation

### Credential Requirements

```typescript
const publicKeyCredentialCreationOptions: PublicKeyCredentialCreationOptions = {
  challenge: new Uint8Array(32), // Random challenge
  rp: {
    name: "H-DCN Portal",
    id: "h-dcn.nl",
  },
  user: {
    id: new TextEncoder().encode(email),
    name: email,
    displayName: email,
  },
  pubKeyCredParams: [
    { alg: -7, type: "public-key" }, // ES256
    { alg: -257, type: "public-key" }, // RS256
  ],
  authenticatorSelection: {
    authenticatorAttachment: "platform", // Prefer platform authenticators
    userVerification: "required",
    requireResidentKey: false,
  },
  timeout: getTimeout(),
  attestation: "none", // No attestation for privacy
};
```

### Challenge Validation

```python
def validate_webauthn_challenge(challenge_response: dict) -> bool:
    # Verify challenge matches stored value
    # Check origin matches expected domain
    # Validate signature against stored public key
    # Ensure counter progression (replay protection)
    return all_validations_pass
```

### Credential Management

```typescript
// Store multiple credentials per user
const storeCredential = (email: string, credentialId: string): void => {
  const existingCredentials = getUserCredentials(email);
  const updatedCredentials = [...existingCredentials, credentialId];

  // Store in Cognito custom attribute (max 2048 characters)
  updateUserAttribute("custom:passkey_cred_ids", updatedCredentials.join(","));
};
```

## Testing and Validation

### Browser Testing Matrix

| Browser          | Desktop | Mobile | Status       |
| ---------------- | ------- | ------ | ------------ |
| Chrome           | ✅      | ✅     | Full support |
| Firefox          | ✅      | ✅     | Full support |
| Safari           | ✅      | ✅     | Full support |
| Edge             | ✅      | ✅     | Full support |
| Samsung Internet | N/A     | ✅     | Full support |

### Device Testing

- **iOS**: Face ID, Touch ID
- **Android**: Fingerprint, Face unlock, PIN
- **Windows**: Windows Hello (Face, Fingerprint, PIN)
- **macOS**: Touch ID, Face ID

### Test Scenarios

1. **Registration Flow**

   ```bash
   # Test passkey registration
   npm test -- --testNamePattern="passkey registration"
   ```

2. **Authentication Flow**

   ```bash
   # Test passkey authentication
   npm test -- --testNamePattern="passkey authentication"
   ```

3. **Cross-Device Flow**
   ```bash
   # Test cross-device authentication
   npm test -- --testNamePattern="cross-device auth"
   ```

## Troubleshooting

### Common Issues

1. **"Credential ID not ArrayBuffer" Error**

   - **Cause**: String passed to WebAuthn API instead of ArrayBuffer
   - **Solution**: Use `base64urlToArrayBuffer()` conversion
   - **Code**: Check `webAuthnService.ts` line 150+

2. **Mobile Timeout Errors**

   - **Cause**: Default 60-second timeout too short for mobile
   - **Solution**: Increase timeout to 300 seconds for mobile devices
   - **Code**: Update timeout configuration

3. **Cognito Attribute Name Too Long**

   - **Cause**: Custom attribute names must be ≤20 characters
   - **Solution**: Use abbreviated names like `passkey_cred_ids`
   - **Code**: Update SAM template

4. **Cross-Device Authentication Fails**
   - **Cause**: WebAuthn not supported on device
   - **Solution**: Implement email verification fallback
   - **Code**: Add fallback authentication flow

### Debug Commands

```typescript
// Enable WebAuthn debugging
localStorage.setItem("webauthn-debug", "true");

// Check WebAuthn support
console.log("WebAuthn supported:", !!window.PublicKeyCredential);

// Test credential creation
navigator.credentials
  .create({ publicKey: options })
  .then((credential) => console.log("Credential created:", credential))
  .catch((error) => console.error("Creation failed:", error));
```

### Logging

```typescript
// Frontend logging
const logWebAuthnEvent = (event: string, data: any): void => {
  console.log(`[WebAuthn] ${event}:`, data);

  // Send to monitoring service
  analytics.track("webauthn_event", {
    event,
    data,
    userAgent: navigator.userAgent,
    timestamp: new Date().toISOString(),
  });
};
```

## Performance Optimization

### Credential Caching

```typescript
// Cache credentials for faster authentication
const credentialCache = new Map<string, PublicKeyCredential>();

const getCachedCredential = (email: string): PublicKeyCredential | null => {
  return credentialCache.get(email) || null;
};
```

### Lazy Loading

```typescript
// Load WebAuthn service only when needed
const loadWebAuthnService = async (): Promise<WebAuthnService> => {
  const { WebAuthnService } = await import("./webAuthnService");
  return new WebAuthnService();
};
```

### Bundle Optimization

```javascript
// Webpack configuration for WebAuthn
module.exports = {
  resolve: {
    fallback: {
      buffer: require.resolve("buffer/"),
      crypto: require.resolve("crypto-browserify"),
    },
  },
};
```

## Future Enhancements

### Planned Features

1. **QR Code Cross-Device Authentication**

   - Generate QR codes for device linking
   - Secure cross-device credential sharing

2. **Credential Management UI**

   - View registered devices
   - Remove old credentials
   - Rename devices

3. **Advanced Security Features**

   - Credential backup and recovery
   - Multi-device synchronization
   - Enterprise policy enforcement

4. **Enhanced Mobile Support**
   - Progressive Web App integration
   - Native mobile app support
   - Offline authentication capabilities

### Integration Roadmap

- **Q1 2025**: QR code authentication
- **Q2 2025**: Credential management UI
- **Q3 2025**: Enterprise features
- **Q4 2025**: Native mobile apps

## Support and Maintenance

### Monitoring

- **Success Rate**: Track authentication success/failure rates
- **Device Distribution**: Monitor device and browser usage
- **Error Patterns**: Identify common failure scenarios

### Updates

- **WebAuthn Spec**: Monitor specification updates
- **Browser Support**: Track new browser features
- **Security Patches**: Apply security updates promptly

### Documentation

- **User Guides**: Maintain user-facing documentation
- **Developer Docs**: Keep technical documentation current
- **Troubleshooting**: Update based on support tickets

---

**Last Updated**: December 29, 2025  
**Version**: Production v2.0  
**Maintained By**: H-DCN Development Team
