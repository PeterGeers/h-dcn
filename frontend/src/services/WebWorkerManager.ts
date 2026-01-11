/**
 * Web Worker Manager for H-DCN Member Reporting
 * 
 * This service manages Web Workers for background data processing tasks.
 * It provides a clean interface for offloading CPU-intensive operations
 * to prevent blocking the main UI thread.
 */

import { Member } from '../types/index';
import { ParquetWorkerMessage, ParquetWorkerResponse, ParquetProcessingStats } from '../types/ParquetTypes';

// ============================================================================
// TYPES
// ============================================================================

export interface WebWorkerTask<T = any> {
  id: string;
  type: 'PROCESS_DATA' | 'APPLY_CALCULATED_FIELDS' | 'APPLY_REGIONAL_FILTER';
  data: any[];
  options?: T;
  resolve: (result: WebWorkerResult) => void;
  reject: (error: Error) => void;
  onProgress?: (progress: number, message?: string) => void;
}

export interface WebWorkerResult {
  data: Member[];
  stats?: ParquetProcessingStats;
}

export interface WebWorkerConfig {
  maxWorkers: number;
  workerScriptPath: string;
  taskTimeout: number; // milliseconds
  enableLogging: boolean;
}

// ============================================================================
// WEB WORKER MANAGER CLASS
// ============================================================================

export class WebWorkerManager {
  private static instance: WebWorkerManager;
  private config: WebWorkerConfig;
  private workers: Worker[] = [];
  private availableWorkers: Worker[] = [];
  private taskQueue: WebWorkerTask[] = [];
  private activeTasks: Map<string, WebWorkerTask> = new Map();
  private workerTaskMap: Map<Worker, string> = new Map();

  private constructor(config: Partial<WebWorkerConfig> = {}) {
    this.config = {
      maxWorkers: Math.max(1, Math.min(navigator.hardwareConcurrency || 2, 4)), // 1-4 workers
      workerScriptPath: '/workers/parquet-data-worker.js',
      taskTimeout: 30000, // 30 seconds
      enableLogging: process.env.NODE_ENV === 'development',
      ...config
    };

    this.log('WebWorkerManager initialized', this.config);
    
    // Temporarily disable worker initialization due to CloudFront MIME type issues
    // this.initializeWorkers();
    this.log('Web Workers temporarily disabled due to CloudFront MIME type issues');
  }

  /**
   * Get singleton instance
   */
  public static getInstance(config?: Partial<WebWorkerConfig>): WebWorkerManager {
    if (!WebWorkerManager.instance) {
      WebWorkerManager.instance = new WebWorkerManager(config);
    }
    return WebWorkerManager.instance;
  }

  // ============================================================================
  // LOGGING
  // ============================================================================

  private log(message: string, data?: any): void {
    if (this.config.enableLogging) {
      console.log(`[WebWorkerManager] ${message}`, data || '');
    }
  }

  private logError(message: string, error?: any): void {
    console.error(`[WebWorkerManager] ${message}`, error || '');
  }

  // ============================================================================
  // WORKER INITIALIZATION
  // ============================================================================

  /**
   * Initialize the worker pool
   */
  private initializeWorkers(): void {
    // Check if Web Workers are supported
    if (typeof Worker === 'undefined') {
      this.logError('Web Workers are not supported in this environment');
      return;
    }

    // Check if workers are disabled via config
    if (this.config.maxWorkers === 0) {
      this.log('Web Workers disabled (maxWorkers = 0)');
      return;
    }

    this.log(`Initializing ${this.config.maxWorkers} workers`);

    for (let i = 0; i < this.config.maxWorkers; i++) {
      try {
        const worker = new Worker(this.config.workerScriptPath);
        
        // Set up message handler
        worker.onmessage = (event) => this.handleWorkerMessage(worker, event);
        
        // Set up error handler
        worker.onerror = (error) => this.handleWorkerError(worker, error);
        
        this.workers.push(worker);
        this.availableWorkers.push(worker);
        
        this.log(`Worker ${i + 1} initialized`);
      } catch (error) {
        this.logError(`Failed to initialize worker ${i + 1}`, error);
      }
    }

    if (this.workers.length === 0) {
      this.logError('No workers could be initialized');
    }
  }

  // ============================================================================
  // WORKER MESSAGE HANDLING
  // ============================================================================

  /**
   * Handle messages from workers
   */
  private handleWorkerMessage(worker: Worker, event: MessageEvent<ParquetWorkerResponse>): void {
    const { type, payload, requestId } = event.data;
    const task = this.activeTasks.get(requestId);

    if (!task) {
      this.logError(`Received message for unknown task: ${requestId}`);
      return;
    }

    switch (type) {
      case 'SUCCESS':
        this.handleTaskSuccess(worker, task, payload);
        break;
        
      case 'ERROR':
        this.handleTaskError(worker, task, payload.error || 'Unknown worker error');
        break;
        
      case 'PROGRESS':
        this.handleTaskProgress(task, payload.progress || 0);
        break;
        
      default:
        this.logError(`Unknown message type from worker: ${type}`);
    }
  }

  /**
   * Handle worker errors
   */
  private handleWorkerError(worker: Worker, error: ErrorEvent): void {
    this.logError('Worker error', error);
    
    const taskId = this.workerTaskMap.get(worker);
    if (taskId) {
      const task = this.activeTasks.get(taskId);
      if (task) {
        this.handleTaskError(worker, task, `Worker error: ${error.message}`);
      }
    }
  }

  /**
   * Handle successful task completion
   */
  private handleTaskSuccess(worker: Worker, task: WebWorkerTask, payload: any): void {
    this.log(`Task completed successfully: ${task.id}`);
    
    // Clean up task
    this.activeTasks.delete(task.id);
    this.workerTaskMap.delete(worker);
    this.availableWorkers.push(worker);
    
    // Resolve the task
    task.resolve({
      data: payload.data || [],
      stats: payload.stats
    });
    
    // Process next task in queue
    this.processNextTask();
  }

  /**
   * Handle task error
   */
  private handleTaskError(worker: Worker, task: WebWorkerTask, errorMessage: string): void {
    this.logError(`Task failed: ${task.id}`, errorMessage);
    
    // Clean up task
    this.activeTasks.delete(task.id);
    this.workerTaskMap.delete(worker);
    this.availableWorkers.push(worker);
    
    // Reject the task
    task.reject(new Error(errorMessage));
    
    // Process next task in queue
    this.processNextTask();
  }

  /**
   * Handle task progress updates
   */
  private handleTaskProgress(task: WebWorkerTask, progress: number, message?: string): void {
    if (task.onProgress) {
      task.onProgress(progress, message);
    }
  }

  // ============================================================================
  // TASK MANAGEMENT
  // ============================================================================

  /**
   * Execute a task using Web Workers
   */
  public executeTask<T = any>(
    type: WebWorkerTask['type'],
    data: any[],
    options?: T,
    onProgress?: (progress: number, message?: string) => void
  ): Promise<WebWorkerResult> {
    return new Promise((resolve, reject) => {
      const taskId = this.generateTaskId();
      
      const task: WebWorkerTask<T> = {
        id: taskId,
        type,
        data,
        options,
        resolve,
        reject,
        onProgress
      };

      this.log(`Queuing task: ${taskId} (${type})`);
      
      // Add timeout
      const timeoutId = setTimeout(() => {
        if (this.activeTasks.has(taskId)) {
          this.handleTaskError(
            this.getWorkerForTask(taskId)!,
            task,
            'Task timeout'
          );
        }
      }, this.config.taskTimeout);

      // Store original reject to clear timeout
      const originalReject = task.reject;
      task.reject = (error) => {
        clearTimeout(timeoutId);
        originalReject(error);
      };

      const originalResolve = task.resolve;
      task.resolve = (result) => {
        clearTimeout(timeoutId);
        originalResolve(result);
      };

      // Queue the task
      this.taskQueue.push(task);
      this.processNextTask();
    });
  }

  /**
   * Process the next task in the queue
   */
  private processNextTask(): void {
    if (this.taskQueue.length === 0 || this.availableWorkers.length === 0) {
      return;
    }

    const task = this.taskQueue.shift()!;
    const worker = this.availableWorkers.shift()!;

    this.log(`Starting task: ${task.id} on worker`);

    // Track the task
    this.activeTasks.set(task.id, task);
    this.workerTaskMap.set(worker, task.id);

    // Send message to worker
    const message: ParquetWorkerMessage = {
      type: task.type,
      payload: {
        data: task.data,
        options: task.options
      },
      requestId: task.id
    };

    worker.postMessage(message);
  }

  /**
   * Get worker for a specific task
   */
  private getWorkerForTask(taskId: string): Worker | undefined {
    for (const [worker, id] of this.workerTaskMap.entries()) {
      if (id === taskId) {
        return worker;
      }
    }
    return undefined;
  }

  /**
   * Generate unique task ID
   */
  private generateTaskId(): string {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // ============================================================================
  // PUBLIC API METHODS
  // ============================================================================

  /**
   * Process data with calculated fields and regional filtering
   */
  public async processData(
    data: any[],
    options: {
      applyCalculatedFields?: boolean;
      applyRegionalFiltering?: boolean;
      regionalFilterOptions?: any;
    } = {},
    onProgress?: (progress: number, message?: string) => void
  ): Promise<WebWorkerResult> {
    if (!this.isAvailable()) {
      throw new Error('Web Workers are not available');
    }

    return this.executeTask('PROCESS_DATA', data, options, onProgress);
  }

  /**
   * Apply calculated fields to member data
   */
  public async applyCalculatedFields(
    data: any[],
    onProgress?: (progress: number, message?: string) => void
  ): Promise<WebWorkerResult> {
    if (!this.isAvailable()) {
      throw new Error('Web Workers are not available');
    }

    return this.executeTask('APPLY_CALCULATED_FIELDS', data, {}, onProgress);
  }

  /**
   * Apply regional filtering to member data
   */
  public async applyRegionalFilter(
    data: any[],
    filterOptions: any,
    onProgress?: (progress: number, message?: string) => void
  ): Promise<WebWorkerResult> {
    if (!this.isAvailable()) {
      throw new Error('Web Workers are not available');
    }

    return this.executeTask('APPLY_REGIONAL_FILTER', data, filterOptions, onProgress);
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Check if Web Workers are available
   */
  public isAvailable(): boolean {
    return typeof Worker !== 'undefined' && this.workers.length > 0;
  }

  /**
   * Get worker pool status
   */
  public getStatus(): {
    totalWorkers: number;
    availableWorkers: number;
    activeTasks: number;
    queuedTasks: number;
  } {
    return {
      totalWorkers: this.workers.length,
      availableWorkers: this.availableWorkers.length,
      activeTasks: this.activeTasks.size,
      queuedTasks: this.taskQueue.length
    };
  }

  /**
   * Terminate all workers and clean up
   */
  public terminate(): void {
    this.log('Terminating all workers');
    
    // Reject all active tasks
    for (const task of this.activeTasks.values()) {
      task.reject(new Error('Worker manager terminated'));
    }
    
    // Reject all queued tasks
    for (const task of this.taskQueue) {
      task.reject(new Error('Worker manager terminated'));
    }
    
    // Terminate all workers
    for (const worker of this.workers) {
      worker.terminate();
    }
    
    // Clear all state
    this.workers = [];
    this.availableWorkers = [];
    this.taskQueue = [];
    this.activeTasks.clear();
    this.workerTaskMap.clear();
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<WebWorkerConfig>): void {
    this.config = { ...this.config, ...newConfig };
    this.log('Configuration updated', this.config);
  }
}

// ============================================================================
// SINGLETON EXPORT
// ============================================================================

export const webWorkerManager = WebWorkerManager.getInstance();
export default WebWorkerManager;