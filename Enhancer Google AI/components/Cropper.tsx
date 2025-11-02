import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { CropRect } from '../types';

interface CropperProps {
  imageSrc: string;
  onCrop: (crop: CropRect) => void;
  onCancel: () => void;
}

type DragState = {
  type: 'move' | 'nw' | 'ne' | 'sw' | 'se' | 'n' | 's' | 'e' | 'w';
  startX: number;
  startY: number;
  initialRect: CropRect;
} | null;

export const Cropper: React.FC<CropperProps> = ({ imageSrc, onCrop, onCancel }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [crop, setCrop] = useState<CropRect>({ x: 0, y: 0, width: 0, height: 0 });
  const [dragState, setDragState] = useState<DragState>(null);

  useEffect(() => {
    const image = imageRef.current;
    if (!image) return;

    const initializeCrop = () => {
      // Initialize crop to be a square in the center of the image
      const imageWidth = image.offsetWidth;
      const imageHeight = image.offsetHeight;
      const size = Math.min(imageWidth, imageHeight) * 0.8;
      const x = (imageWidth - size) / 2;
      const y = (imageHeight - size) / 2;
      setCrop({ x, y, width: size, height: size });
    };

    if (image.complete) {
      initializeCrop();
    } else {
      image.onload = initializeCrop;
    }
  }, [imageSrc]);

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>, type: NonNullable<DragState>['type']) => {
    e.preventDefault();
    e.stopPropagation();
    setDragState({ type, startX: e.clientX, startY: e.clientY, initialRect: crop });
  };
  
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!dragState || !containerRef.current) return;
    
    const dx = e.clientX - dragState.startX;
    const dy = e.clientY - dragState.startY;
    const { initialRect } = dragState;
    let newRect = { ...initialRect };

    switch (dragState.type) {
      case 'move':
        newRect.x = initialRect.x + dx;
        newRect.y = initialRect.y + dy;
        break;
      case 'nw':
        newRect.x = initialRect.x + dx;
        newRect.y = initialRect.y + dy;
        newRect.width = initialRect.width - dx;
        newRect.height = initialRect.height - dy;
        break;
      case 'ne':
        newRect.y = initialRect.y + dy;
        newRect.width = initialRect.width + dx;
        newRect.height = initialRect.height - dy;
        break;
      case 'sw':
        newRect.x = initialRect.x + dx;
        newRect.width = initialRect.width - dx;
        newRect.height = initialRect.height + dy;
        break;
      case 'se':
        newRect.width = initialRect.width + dx;
        newRect.height = initialRect.height + dy;
        break;
      case 'n':
        newRect.y = initialRect.y + dy;
        newRect.height = initialRect.height - dy;
        break;
      case 's':
        newRect.height = initialRect.height + dy;
        break;
      case 'w':
        newRect.x = initialRect.x + dx;
        newRect.width = initialRect.width - dx;
        break;
      case 'e':
        newRect.width = initialRect.width + dx;
        break;
    }

    const container = containerRef.current.getBoundingClientRect();

    // 1. Ensure minimum size, adjusting position if needed to prevent flipping
    if (newRect.width < 20) {
      if (['nw', 'sw', 'w'].includes(dragState.type)) {
        newRect.x = newRect.x + newRect.width - 20;
      }
      newRect.width = 20;
    }
    if (newRect.height < 20) {
      if (['nw', 'ne', 'n'].includes(dragState.type)) {
        newRect.y = newRect.y + newRect.height - 20;
      }
      newRect.height = 20;
    }

    // 2. Clamp to container based on drag type
    if (dragState.type === 'move') {
      newRect.x = Math.max(0, Math.min(newRect.x, container.width - newRect.width));
      newRect.y = Math.max(0, Math.min(newRect.y, container.height - newRect.height));
    } else {
      // For resizing, clamp each edge individually so the box can't leave the container
      if (newRect.x < 0) {
        newRect.width += newRect.x; // shrink width by the amount it's off-screen
        newRect.x = 0;
      }
      if (newRect.y < 0) {
        newRect.height += newRect.y; // shrink height
        newRect.y = 0;
      }
      if (newRect.x + newRect.width > container.width) {
        newRect.width = container.width - newRect.x;
      }
      if (newRect.y + newRect.height > container.height) {
        newRect.height = container.height - newRect.y;
      }
    }

    setCrop(newRect);

  }, [dragState]);

  const handleMouseUp = useCallback(() => {
    setDragState(null);
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const handleApplyCrop = () => {
    if (!imageRef.current) return;
    const image = imageRef.current;
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;
    
    const finalCrop: CropRect = {
      x: crop.x * scaleX,
      y: crop.y * scaleY,
      width: crop.width * scaleX,
      height: crop.height * scaleY,
    };
    onCrop(finalCrop);
  };
  
  return (
    <div
      ref={containerRef}
      className="relative select-none w-full h-full flex items-center justify-center"
      style={{ touchAction: 'none' }}
    >
      <img
        ref={imageRef}
        src={imageSrc}
        alt="Crop preview"
        className="max-w-full max-h-full object-contain pointer-events-none"
      />
      <div
        className="absolute top-0 left-0 w-full h-full"
        style={{
            top: imageRef.current?.offsetTop,
            left: imageRef.current?.offsetLeft,
            width: imageRef.current?.offsetWidth,
            height: imageRef.current?.offsetHeight,
        }}
      >
        {/* Overlay */}
        <div
          className="absolute top-0 left-0 w-full h-full bg-black/70 pointer-events-none"
          style={{
            clipPath: `polygon(
              0% 0%, 100% 0%, 100% 100%, 0% 100%,
              ${crop.x}px ${crop.y}px,
              ${crop.x}px ${crop.y + crop.height}px,
              ${crop.x + crop.width}px ${crop.y + crop.height}px,
              ${crop.x + crop.width}px ${crop.y}px,
              ${crop.x}px ${crop.y}px
            )`,
          }}
        ></div>
        {/* Crop box */}
        <div
          className="absolute border-2 border-dashed border-white cursor-move"
          style={{
            left: crop.x,
            top: crop.y,
            width: crop.width,
            height: crop.height,
          }}
          onMouseDown={(e) => handleMouseDown(e, 'move')}
        >
          {/* Corner Handles */}
          <div onMouseDown={(e) => handleMouseDown(e, 'nw')} className="absolute -top-1.5 -left-1.5 w-3 h-3 bg-white rounded-full cursor-nwse-resize z-10"></div>
          <div onMouseDown={(e) => handleMouseDown(e, 'ne')} className="absolute -top-1.5 -right-1.5 w-3 h-3 bg-white rounded-full cursor-nesw-resize z-10"></div>
          <div onMouseDown={(e) => handleMouseDown(e, 'sw')} className="absolute -bottom-1.5 -left-1.5 w-3 h-3 bg-white rounded-full cursor-nesw-resize z-10"></div>
          <div onMouseDown={(e) => handleMouseDown(e, 'se')} className="absolute -bottom-1.5 -right-1.5 w-3 h-3 bg-white rounded-full cursor-nwse-resize z-10"></div>
          
          {/* Edge Handles (invisible grab areas) */}
          <div onMouseDown={(e) => handleMouseDown(e, 'n')} className="absolute top-[-4px] left-[10px] right-[10px] h-[8px] cursor-ns-resize"></div>
          <div onMouseDown={(e) => handleMouseDown(e, 's')} className="absolute bottom-[-4px] left-[10px] right-[10px] h-[8px] cursor-ns-resize"></div>
          <div onMouseDown={(e) => handleMouseDown(e, 'w')} className="absolute left-[-4px] top-[10px] bottom-[10px] w-[8px] cursor-ew-resize"></div>
          <div onMouseDown={(e) => handleMouseDown(e, 'e')} className="absolute right-[-4px] top-[10px] bottom-[10px] w-[8px] cursor-ew-resize"></div>
        </div>
      </div>
      <div className="absolute bottom-4 flex space-x-4 z-20">
        <button onClick={onCancel} className="bg-slate-700/80 backdrop-blur-sm hover:bg-slate-600 text-white font-bold py-2 px-6 rounded-lg transition-colors">Cancel</button>
        <button onClick={handleApplyCrop} className="bg-indigo-600/90 backdrop-blur-sm hover:bg-indigo-500 text-white font-bold py-2 px-6 rounded-lg transition-colors">Apply Crop</button>
      </div>
    </div>
  );
};