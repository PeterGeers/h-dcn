import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  VStack,
  Text,
  Alert,
  AlertIcon,
  Heading,
  Code,
  List,
  ListItem,
  ListIcon,
  Badge,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Progress,
  Divider,
} from '@chakra-ui/react';
import { CheckIcon, WarningIcon, InfoIcon, CloseIcon } from '@chakra-ui/icons';
import { WebAuthnService } from '../../services/webAuthnService';

interface BrowserTestResult {
  testName: string;
  status: 'pass' | 'fail' | 'warning' | 'info';
  message: string;
  details?: any;
  timestamp: string;
}

interface BrowserCompatibilityInfo {
  browserName: string;
  browserVersion: string;
  platform: string;
  isMobile: boolean;
  webAuthnSupported: boolean;
  platformAuthenticator: boolean;
  userAgent: string;
  supportLevel: 'full' | 'partial' | 'none';
  recommendations: string[];
}

export function BrowserCompatibilityTest() {
  const [testResults, setTestResults] = useState<BrowserTestResult[]>([]);
  const [browserInfo, setBrowserInfo] = useState<BrowserCompatibilityInfo | null>(null);
  const [testing, setTesting] = useState(false);
  const [currentTest, setCurrentTest] = useState('');

  useEffect(() => {
    analyzeBrowserCompatibility();
  }, []);

  const addTestResult = (testName: string, status: 'pass' | 'fail' | 'warning' | 'info', message: string, details?: any) => {
    const result: BrowserTestResult = {
      testName,
      status,
      message,
      details,
      timestamp: new Date().toLocaleTimeString(),
    };
    setTestResults(prev => [...prev, result]);
  };

  const analyzeBrowserCompatibility = async () => {
    const userAgent = navigator.userAgent;
    
    // Detect browser and version
    let browserName = 'Unknown';
    let browserVersion = 'Unknown';
    
    if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) {
      browserName = 'Chrome';
      const match = userAgent.match(/Chrome\/(\d+)/);
      browserVersion = match ? match[1] : 'Unknown';
    } else if (userAgent.includes('Edg')) {
      browserName = 'Edge';
      const match = userAgent.match(/Edg\/(\d+)/);
      browserVersion = match ? match[1] : 'Unknown';
    } else if (userAgent.includes('Firefox')) {
      browserName = 'Firefox';
      const match = userAgent.match(/Firefox\/(\d+)/);
      browserVersion = match ? match[1] : 'Unknown';
    } else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
      browserName = 'Safari';
      const match = userAgent.match(/Version\/(\d+)/);
      browserVersion = match ? match[1] : 'Unknown';
    }

    // Detect platform
    let platform = 'Unknown';
    if (userAgent.includes('Windows')) platform = 'Windows';
    else if (userAgent.includes('Mac')) platform = 'macOS';
    else if (userAgent.includes('Linux')) platform = 'Linux';
    else if (userAgent.includes('Android')) platform = 'Android';
    else if (userAgent.includes('iPhone') || userAgent.includes('iPad')) platform = 'iOS';

    const isMobile = WebAuthnService.isMobileDevice();
    const webAuthnSupported = WebAuthnService.isSupported();
    const platformAuthenticator = await WebAuthnService.isPlatformAuthenticatorAvailable();

    // Determine support level and recommendations
    let supportLevel: 'full' | 'partial' | 'none' = 'none';
    const recommendations: string[] = [];

    if (webAuthnSupported) {
      if (platformAuthenticator) {
        supportLevel = 'full';
        recommendations.push('✅ Full WebAuthn support with platform authenticator');
      } else {
        supportLevel = 'partial';
        recommendations.push('⚠️ WebAuthn supported but no platform authenticator detected');
        recommendations.push('💡 Consider using external security keys or cross-device authentication');
      }
    } else {
      supportLevel = 'none';
      recommendations.push('❌ WebAuthn not supported');
      recommendations.push('🔄 Please update your browser or use Chrome/Edge/Safari');
    }

    // Browser-specific recommendations
    if (browserName === 'Chrome' || browserName === 'Edge') {
      if (parseInt(browserVersion) >= 67) {
        recommendations.push('✅ Browser version supports WebAuthn');
      } else {
        recommendations.push('⚠️ Browser version may have limited WebAuthn support');
        recommendations.push('🔄 Update to latest version for best experience');
      }
    } else if (browserName === 'Safari') {
      if (parseInt(browserVersion) >= 14) {
        recommendations.push('✅ Safari version supports WebAuthn');
      } else {
        recommendations.push('⚠️ Safari version may have limited WebAuthn support');
        recommendations.push('🔄 Update to Safari 14+ for WebAuthn support');
      }
    } else if (browserName === 'Firefox') {
      if (parseInt(browserVersion) >= 60) {
        recommendations.push('✅ Firefox version supports WebAuthn');
      } else {
        recommendations.push('⚠️ Firefox version may have limited WebAuthn support');
        recommendations.push('🔄 Update to Firefox 60+ for WebAuthn support');
      }
    }

    // Platform-specific recommendations
    if (platform === 'Windows') {
      recommendations.push('💡 Windows Hello provides excellent platform authenticator support');
    } else if (platform === 'macOS') {
      recommendations.push('💡 Touch ID and Face ID provide excellent platform authenticator support');
    } else if (platform === 'iOS') {
      recommendations.push('💡 Face ID and Touch ID provide excellent platform authenticator support');
    } else if (platform === 'Android') {
      recommendations.push('💡 Fingerprint and face unlock provide platform authenticator support');
    }

    setBrowserInfo({
      browserName,
      browserVersion,
      platform,
      isMobile,
      webAuthnSupported,
      platformAuthenticator,
      userAgent,
      supportLevel,
      recommendations,
    });
  };

  const runCompatibilityTests = async () => {
    setTesting(true);
    setTestResults([]);

    try {
      // Test 1: WebAuthn API availability
      setCurrentTest('Testing WebAuthn API availability...');
      const webAuthnSupported = WebAuthnService.isSupported();
      addTestResult(
        'WebAuthn API Support',
        webAuthnSupported ? 'pass' : 'fail',
        webAuthnSupported ? 'WebAuthn API is available' : 'WebAuthn API is not available',
        { supported: webAuthnSupported }
      );

      if (!webAuthnSupported) {
        addTestResult(
          'Browser Compatibility',
          'fail',
          'Browser does not support WebAuthn. Please use Chrome 67+, Edge 18+, Firefox 60+, or Safari 14+',
        );
        setTesting(false);
        setCurrentTest('');
        return;
      }

      // Test 2: Platform authenticator availability
      setCurrentTest('Testing platform authenticator availability...');
      const platformAuth = await WebAuthnService.isPlatformAuthenticatorAvailable();
      addTestResult(
        'Platform Authenticator',
        platformAuth ? 'pass' : 'warning',
        platformAuth ? 'Platform authenticator is available' : 'Platform authenticator is not available',
        { available: platformAuth }
      );

      // Test 3: Browser-specific feature detection
      setCurrentTest('Testing browser-specific features...');
      const browserInfo = WebAuthnService.getBrowserInfo();
      addTestResult(
        'Browser Information',
        'info',
        `Detected: ${browserInfo.userAgent}`,
        browserInfo
      );

      // Test 4: Mock passkey registration
      setCurrentTest('Testing passkey registration capability...');
      try {
        const mockOptions = {
          challenge: 'test-challenge-' + Date.now(),
          rp: {
            name: 'H-DCN Test',
            id: window.location.hostname,
          },
          user: {
            id: 'test@example.com',
            name: 'test@example.com',
            displayName: 'Test User',
          },
          pubKeyCredParams: [
            { type: 'public-key' as const, alg: -7 },
            { type: 'public-key' as const, alg: -257 },
          ],
          authenticatorSelection: {
            authenticatorAttachment: 'platform' as const,
            userVerification: 'preferred' as const,
            requireResidentKey: false,
          },
          timeout: 10000, // Short timeout for testing
          attestation: 'none' as const,
        };

        // This will likely fail due to user interaction requirement, but we can test the API
        try {
          await WebAuthnService.registerPasskey(mockOptions);
          addTestResult(
            'Passkey Registration Test',
            'pass',
            'Passkey registration completed successfully',
          );
        } catch (error: any) {
          if (error.name === 'NotAllowedError') {
            addTestResult(
              'Passkey Registration Test',
              'pass',
              'Passkey registration API is functional (user cancelled, which is expected)',
              { error: error.name }
            );
          } else {
            addTestResult(
              'Passkey Registration Test',
              'warning',
              `Passkey registration test failed: ${error.message}`,
              { error: error.name, message: error.message }
            );
          }
        }
      } catch (error: any) {
        addTestResult(
          'Passkey Registration Test',
          'fail',
          `Passkey registration test failed: ${error.message}`,
          { error: error.name, message: error.message }
        );
      }

      // Test 5: Cross-device authentication capability
      setCurrentTest('Testing cross-device authentication capability...');
      const supportsCrossDevice = WebAuthnService.shouldOfferCrossDeviceAuth();
      addTestResult(
        'Cross-Device Authentication',
        supportsCrossDevice ? 'pass' : 'info',
        supportsCrossDevice ? 'Cross-device authentication is supported' : 'Cross-device authentication not recommended for this device',
        { supported: supportsCrossDevice }
      );

      // Test 6: Security context (HTTPS requirement)
      setCurrentTest('Testing security context...');
      const isSecureContext = window.isSecureContext;
      addTestResult(
        'Secure Context (HTTPS)',
        isSecureContext ? 'pass' : 'fail',
        isSecureContext ? 'Running in secure context (HTTPS)' : 'Not running in secure context - WebAuthn requires HTTPS',
        { secure: isSecureContext }
      );

    } catch (error: any) {
      addTestResult(
        'Compatibility Test Error',
        'fail',
        `Test suite failed: ${error.message}`,
        { error: error.name, message: error.message }
      );
    } finally {
      setTesting(false);
      setCurrentTest('');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass': return CheckIcon;
      case 'fail': return CloseIcon;
      case 'warning': return WarningIcon;
      case 'info': return InfoIcon;
      default: return InfoIcon;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass': return 'green';
      case 'fail': return 'red';
      case 'warning': return 'yellow';
      case 'info': return 'blue';
      default: return 'gray';
    }
  };

  const getSupportLevelColor = (level: string) => {
    switch (level) {
      case 'full': return 'green';
      case 'partial': return 'yellow';
      case 'none': return 'red';
      default: return 'gray';
    }
  };

  return (
    <Box maxW="6xl" mx="auto" p={6}>
      <VStack spacing={6}>
        <Box textAlign="center">
          <Heading color="orange.400" size="lg">WebAuthn Browser Compatibility Test</Heading>
          <Text color="gray.400" mt={2}>
            Comprehensive testing of WebAuthn/Passkey support across browsers and platforms
          </Text>
        </Box>

        {browserInfo && (
          <Box w="full" p={6} bg="gray.800" borderRadius="md">
            <Heading size="md" color="orange.400" mb={4}>Browser Analysis</Heading>
            
            <Table variant="simple" size="sm">
              <Tbody>
                <Tr>
                  <Td fontWeight="bold" color="gray.300">Browser</Td>
                  <Td color="white">{browserInfo.browserName} {browserInfo.browserVersion}</Td>
                </Tr>
                <Tr>
                  <Td fontWeight="bold" color="gray.300">Platform</Td>
                  <Td color="white">{browserInfo.platform} {browserInfo.isMobile ? '(Mobile)' : '(Desktop)'}</Td>
                </Tr>
                <Tr>
                  <Td fontWeight="bold" color="gray.300">WebAuthn Support</Td>
                  <Td>
                    <Badge colorScheme={browserInfo.webAuthnSupported ? 'green' : 'red'}>
                      {browserInfo.webAuthnSupported ? 'Supported' : 'Not Supported'}
                    </Badge>
                  </Td>
                </Tr>
                <Tr>
                  <Td fontWeight="bold" color="gray.300">Platform Authenticator</Td>
                  <Td>
                    <Badge colorScheme={browserInfo.platformAuthenticator ? 'green' : 'yellow'}>
                      {browserInfo.platformAuthenticator ? 'Available' : 'Not Available'}
                    </Badge>
                  </Td>
                </Tr>
                <Tr>
                  <Td fontWeight="bold" color="gray.300">Support Level</Td>
                  <Td>
                    <Badge colorScheme={getSupportLevelColor(browserInfo.supportLevel)} size="lg">
                      {browserInfo.supportLevel.toUpperCase()}
                    </Badge>
                  </Td>
                </Tr>
              </Tbody>
            </Table>

            <Box mt={4}>
              <Text fontWeight="bold" color="gray.300" mb={2}>Recommendations:</Text>
              <List spacing={1}>
                {browserInfo.recommendations.map((rec, index) => (
                  <ListItem key={index} color="gray.300" fontSize="sm">
                    {rec}
                  </ListItem>
                ))}
              </List>
            </Box>
          </Box>
        )}

        <VStack spacing={3} w="full">
          <Button
            colorScheme="orange"
            size="lg"
            width="full"
            onClick={runCompatibilityTests}
            isLoading={testing}
            loadingText={currentTest || "Running tests..."}
          >
            Run Comprehensive Compatibility Tests
          </Button>
          
          {testing && (
            <Box w="full">
              <Progress isIndeterminate colorScheme="orange" size="sm" />
              <Text color="gray.400" fontSize="sm" mt={2} textAlign="center">
                {currentTest}
              </Text>
            </Box>
          )}
        </VStack>

        {testResults.length > 0 && (
          <Box w="full" p={6} bg="gray.900" borderRadius="md">
            <Heading size="md" color="orange.400" mb={4}>Test Results</Heading>
            <VStack spacing={3} align="stretch">
              {testResults.map((result, index) => (
                <Box key={index} p={4} bg="gray.800" borderRadius="md">
                  <Box display="flex" alignItems="center" mb={2}>
                    <ListIcon 
                      as={getStatusIcon(result.status)} 
                      color={`${getStatusColor(result.status)}.400`}
                    />
                    <Badge colorScheme={getStatusColor(result.status)} mr={3}>
                      {result.status.toUpperCase()}
                    </Badge>
                    <Text fontWeight="bold" color="white" flex="1">{result.testName}</Text>
                    <Text fontSize="sm" color="gray.400">{result.timestamp}</Text>
                  </Box>
                  <Text color="gray.300" mb={2}>{result.message}</Text>
                  {result.details && (
                    <Code display="block" whiteSpace="pre-wrap" fontSize="xs" p={2} bg="gray.700">
                      {JSON.stringify(result.details, null, 2)}
                    </Code>
                  )}
                </Box>
              ))}
            </VStack>
          </Box>
        )}

        <Divider />

        <Box w="full" p={4} bg="blue.900" borderRadius="md">
          <Heading size="sm" color="blue.300" mb={2}>Browser Support Matrix</Heading>
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th color="blue.200">Browser</Th>
                <Th color="blue.200">Desktop</Th>
                <Th color="blue.200">Mobile</Th>
                <Th color="blue.200">Platform Auth</Th>
                <Th color="blue.200">Notes</Th>
              </Tr>
            </Thead>
            <Tbody>
              <Tr>
                <Td color="white">Chrome 67+</Td>
                <Td><Badge colorScheme="green">Full</Badge></Td>
                <Td><Badge colorScheme="green">Full</Badge></Td>
                <Td><Badge colorScheme="green">Yes</Badge></Td>
                <Td color="gray.300" fontSize="xs">Best support</Td>
              </Tr>
              <Tr>
                <Td color="white">Edge 18+</Td>
                <Td><Badge colorScheme="green">Full</Badge></Td>
                <Td><Badge colorScheme="green">Full</Badge></Td>
                <Td><Badge colorScheme="green">Yes</Badge></Td>
                <Td color="gray.300" fontSize="xs">Windows Hello</Td>
              </Tr>
              <Tr>
                <Td color="white">Safari 14+</Td>
                <Td><Badge colorScheme="green">Full</Badge></Td>
                <Td><Badge colorScheme="green">Full</Badge></Td>
                <Td><Badge colorScheme="green">Yes</Badge></Td>
                <Td color="gray.300" fontSize="xs">Touch/Face ID</Td>
              </Tr>
              <Tr>
                <Td color="white">Firefox 60+</Td>
                <Td><Badge colorScheme="yellow">Partial</Badge></Td>
                <Td><Badge colorScheme="yellow">Partial</Badge></Td>
                <Td><Badge colorScheme="yellow">Limited</Badge></Td>
                <Td color="gray.300" fontSize="xs">Basic support</Td>
              </Tr>
            </Tbody>
          </Table>
          
          <Box mt={4} p={3} bg="blue.800" borderRadius="md">
            <Text color="blue.200" fontSize="sm" mb={2}>
              📋 <strong>Complete Documentation Available</strong>
            </Text>
            <Text color="blue.300" fontSize="xs">
              For detailed compatibility information, testing procedures, and implementation guidelines, 
              see the comprehensive WebAuthn compatibility matrix documentation.
            </Text>
          </Box>
        </Box>
      </VStack>
    </Box>
  );
}

export default BrowserCompatibilityTest;