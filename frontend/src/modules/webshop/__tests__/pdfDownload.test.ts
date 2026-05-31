/**
 * PDF Download Service Tests
 *
 * Tests for the pdfDownloadService that handles downloading order confirmation PDFs.
 * Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
 */

import { downloadOrderPdf } from '../services/pdfDownloadService';

// Mock the auth headers utility
jest.mock('../../../utils/authHeaders', () => ({
  getAuthHeadersForGet: jest.fn(),
}));

import { getAuthHeadersForGet } from '../../../utils/authHeaders';

const mockedGetAuthHeaders = getAuthHeadersForGet as jest.MockedFunction<typeof getAuthHeadersForGet>;

describe('pdfDownloadService', () => {
  let mockFetch: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    // Mock global fetch
    mockFetch = jest.fn();
    global.fetch = mockFetch;

    // Default: auth headers resolve successfully
    mockedGetAuthHeaders.mockResolvedValue({
      Authorization: 'Bearer test-jwt-token',
    });

    // Mock URL.createObjectURL and URL.revokeObjectURL
    global.URL.createObjectURL = jest.fn(() => 'blob:http://localhost/fake-blob-url');
    global.URL.revokeObjectURL = jest.fn();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  describe('API call with correct URL and auth headers', () => {
    test('should call fetch with correct URL containing the orderId', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/pdf' }),
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(10)),
      });

      const promise = downloadOrderPdf('ORD-12345');
      jest.runAllTimers();
      await promise;

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/orders/ORD-12345/pdf');
    });

    test('should encode special characters in orderId', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/pdf' }),
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(10)),
      });

      const promise = downloadOrderPdf('ORD/123 456');
      jest.runAllTimers();
      await promise;

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain(encodeURIComponent('ORD/123 456'));
    });

    test('should include auth headers from getAuthHeadersForGet', async () => {
      mockedGetAuthHeaders.mockResolvedValue({
        Authorization: 'Bearer my-specific-token',
      });

      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/pdf' }),
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(10)),
      });

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      await promise;

      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers).toMatchObject({
        Authorization: 'Bearer my-specific-token',
        Accept: 'application/pdf',
      });
    });

    test('should use GET method', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/pdf' }),
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(10)),
      });

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      await promise;

      const [, options] = mockFetch.mock.calls[0];
      expect(options.method).toBe('GET');
    });
  });

  describe('Blob creation and download trigger on success', () => {
    test('should create blob and trigger download on successful binary PDF response', async () => {
      const pdfBytes = new ArrayBuffer(100);
      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/pdf' }),
        arrayBuffer: () => Promise.resolve(pdfBytes),
      });

      // Spy on document methods for download trigger
      const mockAnchor = {
        href: '',
        download: '',
        style: { display: '' },
        click: jest.fn(),
      };
      jest.spyOn(document, 'createElement').mockReturnValue(mockAnchor as unknown as HTMLElement);
      jest.spyOn(document.body, 'appendChild').mockImplementation(() => mockAnchor as unknown as Node);
      jest.spyOn(document.body, 'removeChild').mockImplementation(() => mockAnchor as unknown as Node);

      const promise = downloadOrderPdf('ORD-99');
      jest.runAllTimers();
      const result = await promise;

      expect(result.success).toBe(true);
      expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
      expect(mockAnchor.download).toBe('orderbevestiging-ORD-99.pdf');
      expect(mockAnchor.click).toHaveBeenCalled();
      expect(URL.revokeObjectURL).toHaveBeenCalled();
    });

    test('should handle base64-encoded response (non-PDF content type)', async () => {
      // Simulate API Gateway returning base64 text
      const base64Content = btoa('fake-pdf-content');
      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        text: () => Promise.resolve(base64Content),
      });

      const mockAnchor = {
        href: '',
        download: '',
        style: { display: '' },
        click: jest.fn(),
      };
      jest.spyOn(document, 'createElement').mockReturnValue(mockAnchor as unknown as HTMLElement);
      jest.spyOn(document.body, 'appendChild').mockImplementation(() => mockAnchor as unknown as Node);
      jest.spyOn(document.body, 'removeChild').mockImplementation(() => mockAnchor as unknown as Node);

      const promise = downloadOrderPdf('ORD-BASE64');
      jest.runAllTimers();
      const result = await promise;

      expect(result.success).toBe(true);
      expect(mockAnchor.download).toBe('orderbevestiging-ORD-BASE64.pdf');
      expect(mockAnchor.click).toHaveBeenCalled();
    });
  });

  describe('Error message display for each error status', () => {
    test('should return unauthorized error for 401 response', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
      });

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      const result = await promise;

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error!.code).toBe('unauthorized');
      expect(result.error!.statusCode).toBe(401);
    });

    test('should return forbidden error for 403 response', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 403,
      });

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      const result = await promise;

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error!.code).toBe('forbidden');
      expect(result.error!.statusCode).toBe(403);
    });

    test('should return not_found error for 404 response', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
      });

      const promise = downloadOrderPdf('ORD-NONEXISTENT');
      jest.runAllTimers();
      const result = await promise;

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error!.code).toBe('not_found');
      expect(result.error!.statusCode).toBe(404);
    });

    test('should return server_error for 500 response', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
      });

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      const result = await promise;

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error!.code).toBe('server_error');
      expect(result.error!.statusCode).toBe(500);
    });

    test('should return timeout error when request is aborted', async () => {
      // Simulate AbortError (timeout)
      const abortError = new Error('The operation was aborted');
      abortError.name = 'AbortError';
      mockFetch.mockRejectedValue(abortError);

      const promise = downloadOrderPdf('ORD-SLOW');
      jest.runAllTimers();
      const result = await promise;

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error!.code).toBe('timeout');
    });

    test('should return network_error for generic fetch failures', async () => {
      mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      const result = await promise;

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error!.code).toBe('network_error');
    });

    test('should return unauthorized error when auth headers fail', async () => {
      mockedGetAuthHeaders.mockRejectedValue(new Error('Authentication required'));

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      const result = await promise;

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error!.code).toBe('unauthorized');
    });
  });

  describe('Loading state management', () => {
    test('should include AbortSignal in fetch request for timeout support', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/pdf' }),
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(10)),
      });

      const mockAnchor = {
        href: '',
        download: '',
        style: { display: '' },
        click: jest.fn(),
      };
      jest.spyOn(document, 'createElement').mockReturnValue(mockAnchor as unknown as HTMLElement);
      jest.spyOn(document.body, 'appendChild').mockImplementation(() => mockAnchor as unknown as Node);
      jest.spyOn(document.body, 'removeChild').mockImplementation(() => mockAnchor as unknown as Node);

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      await promise;

      const [, options] = mockFetch.mock.calls[0];
      expect(options.signal).toBeDefined();
      expect(options.signal).toBeInstanceOf(AbortSignal);
    });

    test('should resolve the promise (not hang) on success', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/pdf' }),
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(10)),
      });

      const mockAnchor = {
        href: '',
        download: '',
        style: { display: '' },
        click: jest.fn(),
      };
      jest.spyOn(document, 'createElement').mockReturnValue(mockAnchor as unknown as HTMLElement);
      jest.spyOn(document.body, 'appendChild').mockImplementation(() => mockAnchor as unknown as Node);
      jest.spyOn(document.body, 'removeChild').mockImplementation(() => mockAnchor as unknown as Node);

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      const result = await promise;

      expect(result).toBeDefined();
      expect(result.success).toBe(true);
    });

    test('should resolve the promise (not hang) on error', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
      });

      const promise = downloadOrderPdf('ORD-001');
      jest.runAllTimers();
      const result = await promise;

      expect(result).toBeDefined();
      expect(result.success).toBe(false);
    });
  });
});
