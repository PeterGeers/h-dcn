
import React, { useState, useCallback } from 'react';
import { Icon } from './Icon';

interface ImageUploadProps {
  onImageUpload: (file: File) => void;
}

export const ImageUpload: React.FC<ImageUploadProps> = ({ onImageUpload }) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onImageUpload(e.target.files[0]);
    }
  };

  const handleDragEvents = useCallback((e: React.DragEvent<HTMLDivElement>, dragging: boolean) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(dragging);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    handleDragEvents(e, false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onImageUpload(e.dataTransfer.files[0]);
    }
  }, [handleDragEvents, onImageUpload]);

  const dropzoneClasses = `flex flex-col items-center justify-center w-full h-full max-w-2xl mx-auto p-8 border-2 border-dashed rounded-xl transition-colors duration-300 ${isDragging ? 'border-indigo-400 bg-slate-700/50' : 'border-slate-600 bg-slate-800/50 hover:border-indigo-500'}`;

  return (
    <div className="flex-grow flex items-center justify-center">
      <div 
        className={dropzoneClasses}
        onDragEnter={(e) => handleDragEvents(e, true)}
        onDragOver={(e) => handleDragEvents(e, true)}
        onDragLeave={(e) => handleDragEvents(e, false)}
        onDrop={handleDrop}
      >
        <Icon name="upload" className="w-16 h-16 text-slate-500 mb-4" />
        <p className="text-xl font-semibold text-slate-300 mb-2">Drag & drop your image here</p>
        <p className="text-slate-400 mb-6">or</p>
        <label htmlFor="file-upload" className="cursor-pointer bg-indigo-600 text-white font-bold py-2 px-6 rounded-lg hover:bg-indigo-500 transition-colors duration-200">
          Browse Files
        </label>
        <input id="file-upload" type="file" className="hidden" accept="image/png, image/jpeg, image/webp" onChange={handleFileChange} />
         <p className="text-xs text-slate-500 mt-6">Supports PNG, JPG, WEBP</p>
      </div>
    </div>
  );
};
