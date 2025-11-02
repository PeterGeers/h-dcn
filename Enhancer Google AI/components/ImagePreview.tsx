import React from 'react';
import { Spinner } from './Spinner';
import { Cropper } from './Cropper';
import type { CropRect } from '../types';

interface ImagePreviewProps {
  originalImage: string | null;
  processedImage: string | null;
  isLoading: boolean;
  loadingMessage: string;
  isCropping: boolean;
  onCrop: (crop: CropRect) => void;
  onCancelCrop: () => void;
}

export const ImagePreview: React.FC<ImagePreviewProps> = ({ 
  originalImage, 
  processedImage, 
  isLoading, 
  loadingMessage,
  isCropping,
  onCrop,
  onCancelCrop,
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
      <div className="flex flex-col items-center p-4 bg-slate-800/50 rounded-lg">
        <h3 className="text-lg font-semibold mb-4 text-slate-400">Original</h3>
        <div className="w-full aspect-square flex items-center justify-center overflow-hidden rounded-md">
            {originalImage && <img src={originalImage} alt="Original" className="max-w-full max-h-full object-contain" />}
        </div>
      </div>
      <div className="flex flex-col items-center p-4 bg-slate-800/50 rounded-lg">
        <h3 className="text-lg font-semibold mb-4 text-slate-400">Processed</h3>
        <div className={`w-full flex items-center justify-center rounded-md bg-slate-900/50 relative ${isCropping ? '' : 'aspect-square overflow-hidden'}`}>
          {isLoading && !isCropping && (
            <div className="absolute inset-0 bg-black/50 flex flex-col items-center justify-center z-10">
              <Spinner />
              <p className="mt-4 text-lg font-medium">{loadingMessage}</p>
            </div>
          )}
          {isCropping && processedImage ? (
            <Cropper imageSrc={processedImage} onCrop={onCrop} onCancel={onCancelCrop} />
          ) : (
            processedImage && <img src={processedImage} alt="Processed" className="max-w-full max-h-full object-contain" />
          )}
        </div>
      </div>
    </div>
  );
};