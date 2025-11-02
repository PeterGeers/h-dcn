
import type { AspectRatio, CropRect } from '../types';

export const base64ToDataAndMimeType = (base64String: string): { data: string, mimeType: string } => {
    const match = base64String.match(/^data:(image\/(?:png|jpeg|gif|webp));base64,(.*)$/);
    if (!match) {
        // Fallback for images that might not have the data URL prefix
        if (base64String.startsWith('/9j/') || base64String.startsWith('iVBORw0KGgoAAAANSUhEUgAA')) {
             // Basic check for JPG and PNG
            const mimeType = base64String.startsWith('/9j/') ? 'image/jpeg' : 'image/png';
            return { mimeType, data: base64String };
        }
        throw new Error('Invalid base64 image string');
    }
    return { mimeType: match[1], data: match[2] };
};

const loadImage = (src: string): Promise<HTMLImageElement> => {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = (err) => reject(err);
        img.src = src.startsWith('data:') ? src : `data:image/png;base64,${src}`;
    });
};

export const resizeImage = async (imageBase64: string, width: number, height: number): Promise<string> => {
    const img = await loadImage(imageBase64);
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Could not get canvas context');
    
    ctx.drawImage(img, 0, 0, width, height);
    
    const { mimeType } = base64ToDataAndMimeType(imageBase64);
    return canvas.toDataURL(mimeType);
};

export const cropImage = async (imageBase64: string, crop: CropRect): Promise<string> => {
    const img = await loadImage(imageBase64);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Could not get canvas context');

    canvas.width = crop.width;
    canvas.height = crop.height;

    ctx.drawImage(
        img,
        crop.x,
        crop.y,
        crop.width,
        crop.height,
        0,
        0,
        crop.width,
        crop.height
    );

    const { mimeType } = base64ToDataAndMimeType(imageBase64);
    return canvas.toDataURL(mimeType);
};


export const getImageDimensions = async (imageBase64: string): Promise<{ width: number, height: number }> => {
    const img = await loadImage(imageBase64);
    return { width: img.width, height: img.height };
};
