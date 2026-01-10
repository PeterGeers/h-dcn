/**
 * React Hook for Web Worker Management
 * 
 * This hook provides a convenient interface for using Web Workers
 * in React components for background data processing tasks.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { webWorkerManager, WebWorkerResult } from '../services/WebWorkerManager';
import { Member } from '../types/index';

// ============================================================================
// TYPES
// ============================================================================

export interface UseWebWorkersOptions {
  enableAutoFallback?: boolean; // Automatically fallback to sync processing if workers fail
  minDataSizeForWorkers?: number; // Minimum data size to use workers (default: 50)
  enableProgressTracking?: boolean; // Track progress for long-running tasks
}

export interface WebWorkerTask {
  id: string;
  type: 'PROCESS_DATA' | 'APPLY_CALCULATED_FIELDS' | 'APPLY_REGIONAL_FILTER';
  status: 'idle' | 'running' | 'completed' | 'error';
  progress: number;
  message?: string;
  error?: string;
  result?: WebWorkerResult;
}

export interface UseWebWorkersReturn {
  // Status
  isAvailable: boolean;
  isProcessing: boolean;
  workerStatus: {
    totalWorkers: number;
    availableWorkers: number;
    activeTasks: number;
    queuedTasks: number;
  } | null;
  
  // Current task
  currentTask: WebWorkerTask | null;
  
  // Processing methods
  processData: (
    data: any[],
    options?: {
      applyCalculatedFields?: boolean;
      applyRegionalFiltering?: boolean;
      regionalFilterOptions?: any;
    }
  ) => Promise<WebWorkerResult>;
  
  applyCalculatedFields: (data: any[]) => Promise<WebWorkerResult>;
  
  applyRegionalFilter: (data: any[], filterOptions: any) => Promise<WebWorkerResult>;
  
  // Utility methods
  clearTask: () => void;
  getTaskHistory: () => WebWorkerTask[];
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useWebWorkers(options: UseWebWorkersOptions = {}): UseWebWorkersReturn {
  const {
    enableAutoFallback = true,
    minDataSizeForWorkers = 50,
    enableProgressTracking = true
  } = options;

  // State
  const [isAvailable, setIsAvailable] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [workerStatus, setWorkerStatus] = useState<UseWebWorkersReturn['workerStatus']>(null);
  const [currentTask, setCurrentTask] = useState<WebWorkerTask | null>(null);
  
  // Task history
  const taskHistoryRef = useRef<WebWorkerTask[]>([]);
  const taskIdCounterRef = useRef(0);

  // Check worker availability on mount
  useEffect(() => {
    const checkAvailability = () => {
      const available = webWorkerManager.isAvailable();
      setIsAvailable(available);
      
      if (available) {
        setWorkerStatus(webWorkerManager.getStatus());
      }
    };

    checkAvailability();
    
    // Update status periodically
    const interval = setInterval(checkAvailability, 5000);
    return () => clearInterval(interval);
  }, []);

  // ============================================================================
  // TASK MANAGEMENT
  // ============================================================================

  const createTask = useCallback((type: WebWorkerTask['type']): WebWorkerTask => {
    const id = `task_${++taskIdCounterRef.current}`;
    return {
      id,
      type,
      status: 'idle',
      progress: 0
    };
  }, []);

  const updateTask = useCallback((updates: Partial<WebWorkerTask>) => {
    setCurrentTask(prev => prev ? { ...prev, ...updates } : null);
  }, []);

  const completeTask = useCallback((result?: WebWorkerResult, error?: string) => {
    setCurrentTask(prev => {
      if (!prev) return null;
      
      const completedTask: WebWorkerTask = {
        ...prev,
        status: error ? 'error' : 'completed',
        progress: error ? prev.progress : 100,
        result,
        error
      };
      
      // Add to history
      taskHistoryRef.current.push(completedTask);
      
      // Keep only last 10 tasks in history
      if (taskHistoryRef.current.length > 10) {
        taskHistoryRef.current = taskHistoryRef.current.slice(-10);
      }
      
      return completedTask;
    });
    
    setIsProcessing(false);
  }, []);

  // ============================================================================
  // PROCESSING METHODS
  // ============================================================================

  const processData = useCallback(async (
    data: any[],
    processingOptions: {
      applyCalculatedFields?: boolean;
      applyRegionalFiltering?: boolean;
      regionalFilterOptions?: any;
    } = {}
  ): Promise<WebWorkerResult> => {
    // Check if we should use Web Workers
    if (!isAvailable || data.length < minDataSizeForWorkers) {
      throw new Error('Web Workers not available or data size too small');
    }

    const task = createTask('PROCESS_DATA');
    setCurrentTask(task);
    setIsProcessing(true);

    try {
      updateTask({ status: 'running', message: 'Starting data processing...' });

      const result = await webWorkerManager.processData(
        data,
        processingOptions,
        enableProgressTracking ? (progress, message) => {
          updateTask({ progress, message });
        } : undefined
      );

      completeTask(result);
      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Processing failed';
      completeTask(undefined, errorMessage);
      
      if (enableAutoFallback) {
        // Could implement fallback logic here
        console.warn('[useWebWorkers] Web Worker processing failed, consider implementing fallback');
      }
      
      throw error;
    }
  }, [isAvailable, minDataSizeForWorkers, enableProgressTracking, enableAutoFallback, createTask, updateTask, completeTask]);

  const applyCalculatedFields = useCallback(async (data: any[]): Promise<WebWorkerResult> => {
    if (!isAvailable || data.length < minDataSizeForWorkers) {
      throw new Error('Web Workers not available or data size too small');
    }

    const task = createTask('APPLY_CALCULATED_FIELDS');
    setCurrentTask(task);
    setIsProcessing(true);

    try {
      updateTask({ status: 'running', message: 'Applying calculated fields...' });

      const result = await webWorkerManager.applyCalculatedFields(
        data,
        enableProgressTracking ? (progress, message) => {
          updateTask({ progress, message });
        } : undefined
      );

      completeTask(result);
      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Calculated fields processing failed';
      completeTask(undefined, errorMessage);
      throw error;
    }
  }, [isAvailable, minDataSizeForWorkers, enableProgressTracking, createTask, updateTask, completeTask]);

  const applyRegionalFilter = useCallback(async (
    data: any[],
    filterOptions: any
  ): Promise<WebWorkerResult> => {
    if (!isAvailable || data.length < minDataSizeForWorkers) {
      throw new Error('Web Workers not available or data size too small');
    }

    const task = createTask('APPLY_REGIONAL_FILTER');
    setCurrentTask(task);
    setIsProcessing(true);

    try {
      updateTask({ status: 'running', message: 'Applying regional filtering...' });

      const result = await webWorkerManager.applyRegionalFilter(
        data,
        filterOptions,
        enableProgressTracking ? (progress, message) => {
          updateTask({ progress, message });
        } : undefined
      );

      completeTask(result);
      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Regional filtering failed';
      completeTask(undefined, errorMessage);
      throw error;
    }
  }, [isAvailable, minDataSizeForWorkers, enableProgressTracking, createTask, updateTask, completeTask]);

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  const clearTask = useCallback(() => {
    setCurrentTask(null);
    setIsProcessing(false);
  }, []);

  const getTaskHistory = useCallback(() => {
    return [...taskHistoryRef.current];
  }, []);

  // ============================================================================
  // RETURN HOOK INTERFACE
  // ============================================================================

  return {
    // Status
    isAvailable,
    isProcessing,
    workerStatus,
    
    // Current task
    currentTask,
    
    // Processing methods
    processData,
    applyCalculatedFields,
    applyRegionalFilter,
    
    // Utility methods
    clearTask,
    getTaskHistory
  };
}

export default useWebWorkers;