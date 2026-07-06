import React, { useState, useRef } from 'react';
import {
  VStack, Button, Alert, AlertIcon, Text, Input, Spinner, HStack, Box,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { analyzePoster, PosterAnalysisResult } from '../../../services/posterAnalysisService';

interface PosterAnalyzerProps {
  onAnalysisComplete: (data: PosterAnalysisResult, file: File) => void;
}

function PosterAnalyzer({ onAnalysisComplete }: PosterAnalyzerProps) {
  const { t } = useTranslation('events');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setSelectedFile(file);
    setError(null);
    setSuccess(false);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError(t('posterAnalysis.noFile'));
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setSuccess(false);

    try {
      const result = await analyzePoster(selectedFile);
      setSuccess(true);
      onAnalysisComplete(result, selectedFile);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <Box w="full" p={3} borderWidth="1px" borderColor="gray.600" borderRadius="md">
      <VStack spacing={3} align="stretch">
        <Text fontWeight="bold" color="orange.300" fontSize="sm">
          {t('posterAnalysis.title')}
        </Text>

        <HStack spacing={2}>
          <Input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            size="sm"
            sx={{
              '::file-selector-button': {
                bg: 'gray.600',
                color: 'white',
                border: 'none',
                borderRadius: 'md',
                px: 3,
                py: 1,
                mr: 2,
                cursor: 'pointer',
              },
            }}
          />
          <Button
            size="sm"
            colorScheme="orange"
            onClick={handleAnalyze}
            isDisabled={!selectedFile || isAnalyzing}
            minW="100px"
          >
            {isAnalyzing ? <Spinner size="xs" /> : t('posterAnalysis.analyze')}
          </Button>
        </HStack>

        {!selectedFile && (
          <Text fontSize="xs" color="gray.400">
            {t('posterAnalysis.selectFile')}
          </Text>
        )}

        {isAnalyzing && (
          <HStack spacing={2}>
            <Spinner size="sm" color="orange.300" />
            <Text fontSize="sm" color="gray.300">
              {t('posterAnalysis.analyzing')}
            </Text>
          </HStack>
        )}

        {error && (
          <Alert status="error" bg="red.900" borderRadius="md" py={2}>
            <AlertIcon />
            <Text fontSize="sm">{t('posterAnalysis.error')}: {error}</Text>
          </Alert>
        )}

        {success && (
          <Alert status="success" bg="green.900" borderRadius="md" py={2}>
            <AlertIcon />
            <Text fontSize="sm">{t('posterAnalysis.success')}</Text>
          </Alert>
        )}
      </VStack>
    </Box>
  );
}

export default PosterAnalyzer;
