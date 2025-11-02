
import React, { useState, useCallback } from 'react';
import { Header } from './components/Header';
import { ImageUpload } from './components/ImageUpload';
import { ControlPanel } from './components/ControlPanel';
import { ImagePreview } from './components/ImagePreview';
import { enhanceImageWithPrompt } from './services/geminiService';
import { resizeImage, cropImage, getImageDimensions } from './utils/imageUtils';
import type { CropRect } from './types';

const App: React.FC = () => {
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingMessage, setLoadingMessage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isCropping, setIsCropping] = useState<boolean>(false);

  const handleImageUpload = (file: File) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64String = reader.result as string;
      setOriginalImage(base64String);
      setProcessedImage(base64String);
      setError(null);
    };
    reader.onerror = () => {
      setError('Failed to read the image file.');
    };
    reader.readAsDataURL(file);
  };

  const handleUploadNew = useCallback(() => {
    setOriginalImage(null);
    setProcessedImage(null);
    setError(null);
    setIsLoading(false);
    setLoadingMessage('');
    setIsCropping(false);
  }, []);

  const handleReset = useCallback(() => {
    setProcessedImage(originalImage);
    setError(null);
    setIsCropping(false);
  }, [originalImage]);

  const processImage = useCallback(async (action: () => Promise<string>, message: string) => {
    if (!processedImage) {
      setError('No image to process.');
      return;
    }
    setIsLoading(true);
    setLoadingMessage(message);
    setError(null);
    try {
      const result = await action();
      setProcessedImage(result);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred during processing.');
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [processedImage]);

  const handleRemoveBackground = useCallback(() => {
    processImage(async () => {
      if (!processedImage) throw new Error("Missing image");
      const mimeType = processedImage.substring(5, processedImage.indexOf(';'));
      const prompt = "remove the background of this image, making it transparent. The subject should be perfectly preserved with clean edges.";
      return enhanceImageWithPrompt(processedImage, mimeType, prompt);
    }, 'Removing background...');
  }, [processImage, processedImage]);

  const handleImproveClarity = useCallback(() => {
    processImage(async () => {
      if (!processedImage) throw new Error("Missing image");
      const mimeType = processedImage.substring(5, processedImage.indexOf(';'));
      const prompt = "Subtly enhance the clarity, sharpness, and color vibrancy of this image. Fix minor lighting issues and make the subject pop, maintaining a natural look. Do not add or remove any elements.";
      return enhanceImageWithPrompt(processedImage, mimeType, prompt);
    }, 'Improving clarity...');
  }, [processImage, processedImage]);

  const handleResize = useCallback((width: number, height: number) => {
    processImage(async () => {
      if (!processedImage) throw new Error("Missing image");
      return resizeImage(processedImage, width, height);
    }, 'Resizing image...');
  }, [processImage, processedImage]);

  const handleResizeByPercentage = useCallback((percentage: number) => {
    if (!processedImage) return;
    
    processImage(async () => {
      if (!processedImage) throw new Error("Missing image");
      const { width, height } = await getImageDimensions(processedImage);
      const newWidth = Math.round(width * (percentage / 100));
      const newHeight = Math.round(height * (percentage / 100));
      return resizeImage(processedImage, newWidth, newHeight);
    }, 'Resizing image...');
  }, [processImage, processedImage]);

  const handleEnterCropMode = useCallback(() => {
    setIsCropping(true);
  }, []);

  const handleCancelCrop = useCallback(() => {
    setIsCropping(false);
  }, []);

  const handleCrop = useCallback((crop: CropRect) => {
    setIsCropping(false);
    processImage(async () => {
      if (!processedImage) throw new Error("Missing image");
      return cropImage(processedImage, crop);
    }, 'Cropping image...');
  }, [processImage, processedImage]);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 flex flex-col">
      <Header />
      <main className="flex-grow container mx-auto p-4 md:p-8 flex flex-col">
        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-300 p-4 rounded-lg mb-6 text-center">
            <strong>Error:</strong> {error}
          </div>
        )}
        {!originalImage ? (
          <ImageUpload onImageUpload={handleImageUpload} />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-grow">
            <div className="lg:col-span-4 xl:col-span-3">
              <ControlPanel
                onRemoveBackground={handleRemoveBackground}
                onImproveClarity={handleImproveClarity}
                onResize={handleResize}
                onResizeByPercentage={handleResizeByPercentage}
                onEnterCropMode={handleEnterCropMode}
                onReset={handleReset}
                onUploadNew={handleUploadNew}
                processedImage={processedImage}
                isLoading={isLoading || isCropping}
              />
            </div>
            <div className="lg:col-span-8 xl:col-span-9">
              <ImagePreview
                originalImage={originalImage}
                processedImage={processedImage}
                isLoading={isLoading}
                loadingMessage={loadingMessage}
                isCropping={isCropping}
                onCrop={handleCrop}
                onCancelCrop={handleCancelCrop}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
