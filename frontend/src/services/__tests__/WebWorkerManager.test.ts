/**
 * Tests for WebWorkerManager
 * 
 * These tests verify the Web Worker management functionality including
 * task queuing, worker pool management, and error handling.
 */

import { WebWorkerManager } from '../WebWorkerManager';

// Mock Worker class for testing
class MockWorker {
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((error: ErrorEvent) => void) | null = null;
  private terminated = false;

  constructor(public scriptPath: string) {
    // Simulate worker initialization
    setTimeout(() => {
      if (this.onmessage && !this.terminated) {
        this.onmessage({
          data: {
            type: 'READY',
            payload: { message: 'Worker ready' },
            requestId: 'init'
          }
        } as MessageEvent);
      }
    }, 10);
  }

  postMessage(message: any) {
    if (this.terminated) return;
    
    // Simulate processing delay
    setTimeout(() => {
      if (this.onmessage && !this.terminated) {
        const { type, payload, requestId } = message;
        
        // Simulate different responses based on message type
        if (type === 'APPLY_CALCULATED_FIELDS') {
          // Simulate progress
          this.onmessage({
            data: {
              type: 'PROGRESS',
              payload: { progress: 50, message: 'Processing...' },
              requestId
            }
          } as MessageEvent);
          
          // Simulate completion
          setTimeout(() => {
            if (this.onmessage && !this.terminated) {
              this.onmessage({
                data: {
                  type: 'SUCCESS',
                  payload: {
                    data: payload.data.map((item: any) => ({
                      ...item,
                      korte_naam: `${item.voornaam} ${item.achternaam}`,
                      leeftijd: 35
                    })),
                    stats: {
                      totalRecords: payload.data.length,
                      processedRecords: payload.data.length,
                      calculatedFieldsComputed: payload.data.length,
                      processingTime: 100
                    }
                  },
                  requestId
                }
              } as MessageEvent);
            }
          }, 50);
        } else if (type === 'APPLY_REGIONAL_FILTER') {
          // Simulate filtering
          const filteredData = payload.data.filter((item: any) => item.regio === 'Noord-Holland');
          this.onmessage({
            data: {
              type: 'SUCCESS',
              payload: {
                data: filteredData,
                stats: {
                  totalRecords: payload.data.length,
                  processedRecords: filteredData.length,
                  regionallyFiltered: payload.data.length - filteredData.length,
                  processingTime: 50
                }
              },
              requestId
            }
          } as MessageEvent);
        } else {
          // Default success response
          this.onmessage({
            data: {
              type: 'SUCCESS',
              payload: { data: payload.data },
              requestId
            }
          } as MessageEvent);
        }
      }
    }, 20);
  }

  terminate() {
    this.terminated = true;
    this.onmessage = null;
    this.onerror = null;
  }
}

// Mock global Worker
(global as any).Worker = MockWorker;
(global as any).navigator = {
  hardwareConcurrency: 4
};

describe('WebWorkerManager', () => {
  let workerManager: WebWorkerManager;

  beforeEach(() => {
    // Create a new instance for each test
    workerManager = WebWorkerManager.getInstance({
      maxWorkers: 2,
      workerScriptPath: '/test-worker.js',
      taskTimeout: 5000,
      enableLogging: false
    });
  });

  afterEach(() => {
    workerManager.terminate();
  });

  describe('Initialization', () => {
    test('should initialize with correct configuration', () => {
      const status = workerManager.getStatus();
      expect(status.totalWorkers).toBe(2);
      expect(status.availableWorkers).toBe(2);
      expect(status.activeTasks).toBe(0);
      expect(status.queuedTasks).toBe(0);
    });

    test('should report availability correctly', () => {
      expect(workerManager.isAvailable()).toBe(true);
    });
  });

  describe('Task Execution', () => {
    test('should execute calculated fields task successfully', async () => {
      const testData = [
        { id: '1', voornaam: 'John', achternaam: 'Doe', geboortedatum: '1990-01-01' },
        { id: '2', voornaam: 'Jane', achternaam: 'Smith', geboortedatum: '1985-05-15' }
      ];

      const result = await workerManager.applyCalculatedFields(testData);

      expect(result.data).toHaveLength(2);
      expect(result.data[0]).toHaveProperty('korte_naam', 'John Doe');
      expect(result.data[0]).toHaveProperty('leeftijd', 35);
      expect(result.stats).toBeDefined();
      expect(result.stats?.calculatedFieldsComputed).toBe(2);
    });

    test('should execute regional filter task successfully', async () => {
      const testData = [
        { id: '1', naam: 'John', regio: 'Noord-Holland' },
        { id: '2', naam: 'Jane', regio: 'Zuid-Holland' },
        { id: '3', naam: 'Bob', regio: 'Noord-Holland' }
      ];

      const filterOptions = {
        userRoles: ['Members_Read', 'Regio_Noord-Holland'],
        userEmail: 'test@example.com'
      };

      const result = await workerManager.applyRegionalFilter(testData, filterOptions);

      expect(result.data).toHaveLength(2); // Both Noord-Holland members
      expect(result.data[0].regio).toBe('Noord-Holland');
      expect(result.stats?.regionallyFiltered).toBe(1); // 1 member filtered out (Zuid-Holland)
    });

    test('should handle progress updates', async () => {
      const testData = [{ id: '1', voornaam: 'John', achternaam: 'Doe' }];
      const progressUpdates: Array<{ progress: number; message?: string }> = [];

      const result = await workerManager.applyCalculatedFields(
        testData,
        (progress, message) => {
          progressUpdates.push({ progress, message });
        }
      );

      expect(result.data).toHaveLength(1);
      expect(progressUpdates.length).toBeGreaterThan(0);
      expect(progressUpdates[0].progress).toBe(50);
    });
  });

  describe('Task Queue Management', () => {
    test('should queue tasks when all workers are busy', async () => {
      const testData = [{ id: '1', voornaam: 'John', achternaam: 'Doe' }];

      // Start multiple tasks simultaneously
      const promises = [
        workerManager.applyCalculatedFields(testData),
        workerManager.applyCalculatedFields(testData),
        workerManager.applyCalculatedFields(testData)
      ];

      const results = await Promise.all(promises);

      expect(results).toHaveLength(3);
      results.forEach(result => {
        expect(result.data).toHaveLength(1);
      });
    });

    test('should update status correctly during task execution', async () => {
      const testData = [{ id: '1', voornaam: 'John', achternaam: 'Doe' }];

      const taskPromise = workerManager.applyCalculatedFields(testData);
      
      // Check status while task is running
      await new Promise(resolve => setTimeout(resolve, 10));
      const statusDuringExecution = workerManager.getStatus();
      
      await taskPromise;
      
      const statusAfterCompletion = workerManager.getStatus();

      expect(statusAfterCompletion.activeTasks).toBe(0);
      expect(statusAfterCompletion.availableWorkers).toBe(2);
    });
  });

  describe('Error Handling', () => {
    test('should handle task timeout', async () => {
      // Create manager with very short timeout
      const shortTimeoutManager = WebWorkerManager.getInstance({
        maxWorkers: 1,
        taskTimeout: 1, // 1ms timeout
        enableLogging: false
      });

      const testData = [{ id: '1', voornaam: 'John', achternaam: 'Doe' }];

      await expect(
        shortTimeoutManager.applyCalculatedFields(testData)
      ).rejects.toThrow('Task timeout');

      shortTimeoutManager.terminate();
    });
  });

  describe('Configuration', () => {
    test('should update configuration correctly', () => {
      workerManager.updateConfig({
        taskTimeout: 10000,
        enableLogging: true
      });

      // Configuration update doesn't have a direct getter, but we can verify
      // it doesn't throw errors and the manager continues to work
      expect(workerManager.isAvailable()).toBe(true);
    });
  });

  describe('Cleanup', () => {
    test('should terminate all workers and reject pending tasks', async () => {
      const testData = [{ id: '1', voornaam: 'John', achternaam: 'Doe' }];

      // Start a task
      const taskPromise = workerManager.applyCalculatedFields(testData);
      
      // Terminate immediately
      workerManager.terminate();

      // Task should be rejected
      await expect(taskPromise).rejects.toThrow('Worker manager terminated');

      // Status should show no workers
      const status = workerManager.getStatus();
      expect(status.totalWorkers).toBe(0);
      expect(status.availableWorkers).toBe(0);
    });
  });
});

describe('WebWorkerManager Edge Cases', () => {
  test('should handle environment without Worker support', () => {
    // Temporarily remove Worker from global
    const originalWorker = (global as any).Worker;
    delete (global as any).Worker;

    const manager = WebWorkerManager.getInstance({
      maxWorkers: 2,
      enableLogging: false
    });

    expect(manager.isAvailable()).toBe(false);
    expect(manager.getStatus().totalWorkers).toBe(0);

    manager.terminate();

    // Restore Worker
    (global as any).Worker = originalWorker;
  });

  test('should handle worker initialization failure', () => {
    // Mock Worker that throws during construction
    const FailingWorker = class {
      constructor() {
        throw new Error('Worker initialization failed');
      }
    };

    const originalWorker = (global as any).Worker;
    (global as any).Worker = FailingWorker;

    const manager = WebWorkerManager.getInstance({
      maxWorkers: 2,
      enableLogging: false
    });

    expect(manager.isAvailable()).toBe(false);
    expect(manager.getStatus().totalWorkers).toBe(0);

    manager.terminate();

    // Restore Worker
    (global as any).Worker = originalWorker;
  });
});