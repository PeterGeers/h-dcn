/**
 * Image Processing Service
 * Ondersteunt verkleinen, bijsnijden, transparantie, kleurversterking en opslaan
 */

interface ResizeOptions {
  width: number;
  height: number;
}

interface CropOptions {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface TransparencyOptions {
  color?: string;
  tolerance?: number;
  removeBackground?: boolean;
}

interface ColorAdjustOptions {
  brightness?: number;
  saturation?: number;
  contrast?: number;
}

interface ProcessImageOptions {
  resize?: ResizeOptions | null;
  crop?: CropOptions | null;
  rotation?: number | null;
  transparency?: TransparencyOptions | null;
  colorAdjust?: ColorAdjustOptions | null;
  outputFormat?: 'png' | 'jpeg';
  quality?: number;
}

interface RgbColor {
  r: number;
  g: number;
  b: number;
}

interface Dimensions {
  width: number;
  height: number;
}

export class ImageProcessor {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;

  constructor() {
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d')!;
  }

  /**
   * Hoofdfunctie voor image processing
   */
  async processImage(imageInput: File | string, options: ProcessImageOptions = {}): Promise<Blob> {
    const {
      resize = null,
      crop = null,
      rotation = null,
      transparency = null,
      colorAdjust = null,
      outputFormat = 'png',
      quality = 0.9
    } = options;

    const img = await this.loadImage(imageInput);
    
    const dimensions = this.calculateDimensions(img, rotation, crop, resize);
    this.canvas.width = dimensions.width;
    this.canvas.height = dimensions.height;

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    this.drawImageWithRotation(img, rotation, crop, resize);

    if (colorAdjust) this.adjustColors(colorAdjust);
    if (transparency) this.applyTransparency(transparency);

    return this.canvasToBlob(outputFormat, quality);
  }

  /**
   * Laad afbeelding van File of URL
   */
  private loadImage(input: File | string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      
      img.onload = () => resolve(img);
      img.onerror = reject;
      
      if (input instanceof File) {
        const reader = new FileReader();
        reader.onload = (e) => {
          if (e.target?.result) {
            img.src = e.target.result as string;
          }
        };
        reader.readAsDataURL(input);
      } else {
        img.src = input;
      }
    });
  }

  /**
   * Bereken canvas afmetingen rekening houdend met rotatie
   */
  private calculateDimensions(
    img: HTMLImageElement, 
    rotation: number | null, 
    crop: CropOptions | null, 
    resize: ResizeOptions | null
  ): Dimensions {
    let width: number, height: number;
    
    if (crop) {
      width = crop.width;
      height = crop.height;
    } else if (resize) {
      width = resize.width;
      height = resize.height;
    } else {
      width = img.width;
      height = img.height;
    }
    
    if (rotation && (Math.abs(rotation) % 180 === 90)) {
      return { width: height, height: width };
    }
    
    return { width, height };
  }

  /**
   * Teken afbeelding op canvas met rotatie
   */
  private drawImageWithRotation(
    img: HTMLImageElement, 
    rotation: number | null, 
    crop: CropOptions | null, 
    resize: ResizeOptions | null
  ): void {
    const centerX = this.canvas.width / 2;
    const centerY = this.canvas.height / 2;
    
    this.ctx.save();
    
    if (rotation) {
      this.ctx.translate(centerX, centerY);
      this.ctx.rotate((rotation * Math.PI) / 180);
      this.ctx.translate(-centerX, -centerY);
    }
    
    if (crop) {
      const drawWidth = rotation && (Math.abs(rotation) % 180 === 90) ? this.canvas.height : this.canvas.width;
      const drawHeight = rotation && (Math.abs(rotation) % 180 === 90) ? this.canvas.width : this.canvas.height;
      
      this.ctx.drawImage(
        img, 
        crop.x, crop.y, crop.width, crop.height,
        (this.canvas.width - drawWidth) / 2, (this.canvas.height - drawHeight) / 2, drawWidth, drawHeight
      );
    } else {
      const drawWidth = rotation && (Math.abs(rotation) % 180 === 90) ? this.canvas.height : this.canvas.width;
      const drawHeight = rotation && (Math.abs(rotation) % 180 === 90) ? this.canvas.width : this.canvas.height;
      
      this.ctx.drawImage(
        img, 
        (this.canvas.width - drawWidth) / 2, (this.canvas.height - drawHeight) / 2, 
        drawWidth, drawHeight
      );
    }
    
    this.ctx.restore();
  }

  /**
   * Pas kleurcorrecties toe
   */
  private adjustColors({ brightness = 1, saturation = 1, contrast = 1 }: ColorAdjustOptions): void {
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
      let r = data[i] / 255;
      let g = data[i + 1] / 255;
      let b = data[i + 2] / 255;

      r *= brightness;
      g *= brightness;
      b *= brightness;

      r = (r - 0.5) * contrast + 0.5;
      g = (g - 0.5) * contrast + 0.5;
      b = (b - 0.5) * contrast + 0.5;

      const gray = 0.299 * r + 0.587 * g + 0.114 * b;
      r = gray + saturation * (r - gray);
      g = gray + saturation * (g - gray);
      b = gray + saturation * (b - gray);

      data[i] = Math.max(0, Math.min(255, Math.round(r * 255)));
      data[i + 1] = Math.max(0, Math.min(255, Math.round(g * 255)));
      data[i + 2] = Math.max(0, Math.min(255, Math.round(b * 255)));
    }

    this.ctx.putImageData(imageData, 0, 0);
  }

  /**
   * Pas transparantie toe
   */
  private applyTransparency({ color = null, tolerance = 10, removeBackground = false }: TransparencyOptions): void {
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const data = imageData.data;

    if (color) {
      const targetColor = this.hexToRgb(color);
      if (targetColor) {
        for (let i = 0; i < data.length; i += 4) {
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];

          const distance = Math.sqrt(
            Math.pow(r - targetColor.r, 2) +
            Math.pow(g - targetColor.g, 2) +
            Math.pow(b - targetColor.b, 2)
          );

          if (distance <= tolerance) {
            data[i + 3] = 0;
          }
        }
      }
    }

    if (removeBackground) {
      this.removeCornerBackground(data, tolerance);
    }

    this.ctx.putImageData(imageData, 0, 0);
  }

  /**
   * Verwijder achtergrond op basis van hoekpixels
   */
  private removeCornerBackground(data: Uint8ClampedArray, tolerance: number): void {
    const width = this.canvas.width;
    const height = this.canvas.height;
    
    const corners = [
      [0, 0],
      [(width - 1) * 4, 0],
      [0, (height - 1) * width * 4],
      [(width - 1) * 4, (height - 1) * width * 4]
    ];
    
    let avgR = 0, avgG = 0, avgB = 0;
    corners.forEach(([x, y]) => {
      const index = y + x;
      avgR += data[index];
      avgG += data[index + 1];
      avgB += data[index + 2];
    });
    
    const bgR = avgR / 4;
    const bgG = avgG / 4;
    const bgB = avgB / 4;

    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];

      const distance = Math.sqrt(
        Math.pow(r - bgR, 2) +
        Math.pow(g - bgG, 2) +
        Math.pow(b - bgB, 2)
      );

      if (distance <= tolerance) {
        data[i + 3] = 0;
      }
    }
  }

  /**
   * Converteer hex kleur naar RGB
   */
  private hexToRgb(hex: string): RgbColor | null {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  }

  /**
   * Converteer canvas naar blob
   */
  private canvasToBlob(format: 'png' | 'jpeg', quality: number): Promise<Blob> {
    return new Promise((resolve) => {
      const mimeType = format === 'jpeg' ? 'image/jpeg' : 'image/png';
      this.canvas.toBlob((blob) => {
        if (blob) resolve(blob);
      }, mimeType, quality);
    });
  }

  /**
   * Download processed image
   */
  async downloadImage(blob: Blob, filename: string = 'processed-image.jpg'): Promise<void> {
    const sanitizedFilename = filename.replace(/[^a-zA-Z0-9.-]/g, '_');
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.setAttribute('download', sanitizedFilename);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

export const processImage = async (imageInput: File | string, options: ProcessImageOptions): Promise<Blob> => {
  const processor = new ImageProcessor();
  return await processor.processImage(imageInput, options);
};