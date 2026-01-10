/**
 * Web Worker Status Component
 * 
 * This component displays the current status of Web Workers and provides
 * visual feedback for background processing tasks.
 */

import React from 'react';
import {
  Box,
  Text,
  Badge,
  Progress,
  VStack,
  HStack,
  Icon,
  Tooltip,
  useColorModeValue
} from '@chakra-ui/react';
import { CheckIcon, WarningIcon } from '@chakra-ui/icons';
import { useWebWorkers } from '../../hooks/useWebWorkers';

// ============================================================================
// TYPES
// ============================================================================

export interface WebWorkerStatusProps {
  showDetails?: boolean;
  compact?: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

export const WebWorkerStatus: React.FC<WebWorkerStatusProps> = ({
  showDetails = false,
  compact = false
}) => {
  const {
    isAvailable,
    isProcessing,
    workerStatus,
    currentTask
  } = useWebWorkers();

  // Theme colors
  const bgColor = useColorModeValue('gray.50', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.600', 'gray.300');

  // Status badge color
  const getStatusColor = () => {
    if (!isAvailable) return 'red';
    if (isProcessing) return 'blue';
    return 'green';
  };

  const getStatusText = () => {
    if (!isAvailable) return 'Unavailable';
    if (isProcessing) return 'Processing';
    return 'Ready';
  };

  const getStatusIcon = () => {
    if (!isAvailable) return WarningIcon;
    if (isProcessing) return WarningIcon; // Use warning for processing
    return CheckIcon;
  };

  // Compact view
  if (compact) {
    return (
      <Tooltip
        label={`Web Workers: ${getStatusText()}${workerStatus ? ` (${workerStatus.availableWorkers}/${workerStatus.totalWorkers} available)` : ''}`}
        placement="top"
      >
        <HStack spacing={2}>
          <Icon as={getStatusIcon()} color={`${getStatusColor()}.500`} />
          <Badge colorScheme={getStatusColor()} size="sm">
            {getStatusText()}
          </Badge>
        </HStack>
      </Tooltip>
    );
  }

  // Full view
  return (
    <Box
      bg={bgColor}
      border="1px"
      borderColor={borderColor}
      borderRadius="md"
      p={4}
      minW="250px"
    >
      <VStack align="stretch" spacing={3}>
        {/* Header */}
        <HStack justify="space-between">
          <HStack spacing={2}>
            <Icon as={CheckIcon} color="orange.400" />
            <Text fontSize="sm" fontWeight="medium" color={textColor}>
              Web Workers
            </Text>
          </HStack>
          <Badge colorScheme={getStatusColor()} size="sm">
            {getStatusText()}
          </Badge>
        </HStack>

        {/* Worker Status */}
        {isAvailable && workerStatus && (
          <VStack align="stretch" spacing={2}>
            <HStack justify="space-between" fontSize="xs" color={textColor}>
              <Text>Available Workers:</Text>
              <Text fontWeight="medium">
                {workerStatus.availableWorkers}/{workerStatus.totalWorkers}
              </Text>
            </HStack>
            
            {(workerStatus.activeTasks > 0 || workerStatus.queuedTasks > 0) && (
              <>
                <HStack justify="space-between" fontSize="xs" color={textColor}>
                  <Text>Active Tasks:</Text>
                  <Text fontWeight="medium">{workerStatus.activeTasks}</Text>
                </HStack>
                
                {workerStatus.queuedTasks > 0 && (
                  <HStack justify="space-between" fontSize="xs" color={textColor}>
                    <Text>Queued Tasks:</Text>
                    <Text fontWeight="medium">{workerStatus.queuedTasks}</Text>
                  </HStack>
                )}
              </>
            )}
          </VStack>
        )}

        {/* Current Task Progress */}
        {currentTask && isProcessing && (
          <VStack align="stretch" spacing={2}>
            <Text fontSize="xs" color={textColor} fontWeight="medium">
              Current Task: {currentTask.type.replace(/_/g, ' ').toLowerCase()}
            </Text>
            
            <Progress
              value={currentTask.progress}
              size="sm"
              colorScheme="blue"
              borderRadius="md"
            />
            
            <HStack justify="space-between" fontSize="xs" color={textColor}>
              <Text>{currentTask.message || 'Processing...'}</Text>
              <Text fontWeight="medium">{Math.round(currentTask.progress)}%</Text>
            </HStack>
          </VStack>
        )}

        {/* Error State */}
        {currentTask?.status === 'error' && (
          <Box
            bg="red.50"
            border="1px"
            borderColor="red.200"
            borderRadius="md"
            p={2}
          >
            <HStack spacing={2}>
              <Icon as={WarningIcon} color="red.500" boxSize={4} />
              <Text fontSize="xs" color="red.600">
                {currentTask.error || 'Processing failed'}
              </Text>
            </HStack>
          </Box>
        )}

        {/* Details */}
        {showDetails && !isAvailable && (
          <Text fontSize="xs" color={textColor}>
            Web Workers are not supported in this browser or environment.
            Processing will use the main thread.
          </Text>
        )}
      </VStack>
    </Box>
  );
};

export default WebWorkerStatus;