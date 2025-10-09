/**
 * Image Processing Service
 * Ondersteunt verkleinen, bijsnijden, transparantie, kleurversterking en opslaan
 */

export class ImageProcessor {
  constructor() {
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d');
  }

  /**
   * Hoofdfunctie voor image processing
   * @param {File|string} imageInput - Image file of URL
   * @param {Object} options - Processing opties
   * @returns {Promise<Blob>} - Processed image als blob
   */
  async processImage(imageInput, options = {}) {
    const {
      resize = null,           // {width: 800, height: 600}
      crop = null,             // {x: 0, y: 0, width: 400, height: 300}
      rotation = null,         // rotation in degrees (90, 180, 270, etc.)
      transparency = null,     // {color: '#ffffff', tolerance: 10} of {removeBackground: true}
      colorAdjust = null,      // {brightness: 1.2, saturation: 1.5, contrast: 1.1}
      outputFormat = 'png',    // 'png' of 'jpeg'
      quality = 0.9            // Voor JPEG quality
    } = options;

    // Laad de afbeelding
    const img = await this.loadImage(imageInput);
    
    // Bepaal canvas afmetingen (rekening houdend met rotatie)
    const dimensions = this.calculateDimensions(img, rotation, crop, resize);
    this.canvas.width = dimensions.width;
    this.canvas.height = dimensions.height;

    // Clear canvas completely
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Teken de afbeelding op canvas (met rotatie)
    this.drawImageWithRotation(img, rotation, crop, resize);

    // Pas bewerkingen toe
    if (colorAdjust) this.adjustColors(colorAdjust);
    if (transparency) this.applyTransparency(transparency);

    // Converteer naar blob
    return this.canvasToBlob(outputFormat, quality);
  }

  /**
   * Laad afbeelding van File of URL
   */
  loadImage(input) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      
      img.onload = () => resolve(img);
      img.onerror = reject;
      
      if (input instanceof File) {
        const reader = new FileReader();
        reader.onload = (e) => img.src = e.target.result;
        reader.readAsDataURL(input);
      } else {
        img.src = input;
      }
    });
  }

  /**
   * Bepaal initiële canvas afmetingen
   */
  getInitialDimensions(img, resize, crop) {
    if (crop) {
      return { width: crop.width, height: crop.height };
    }
    if (resize) {
      return { width: resize.width, height: resize.height };
    }
    return { width: img.width, height: img.height };
  }

  /**
   * Bereken canvas afmetingen rekening houdend met rotatie
   */
  calculateDimensions(img, rotation, crop, resize) {
    let width, height;
    
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
    
    // Voor 90° en 270° rotaties, wissel breedte en hoogte om
    if (rotation && (Math.abs(rotation) % 180 === 90)) {
      return { width: height, height: width };
    }
    
    return { width, height };
  }

  /**
   * Teken afbeelding op canvas met rotatie
   */
  drawImageWithRotation(img, rotation, crop, resize) {
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
  adjustColors({ brightness = 1, saturation = 1, contrast = 1 }) {
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
      let r = data[i];
      let g = data[i + 1];
      let b = data[i + 2];

      // Normalize to 0-1 range
      r /= 255;
      g /= 255;
      b /= 255;

      // Apply brightness
      r *= brightness;
      g *= brightness;
      b *= brightness;

      // Apply contrast
      r = (r - 0.5) * contrast + 0.5;
      g = (g - 0.5) * contrast + 0.5;
      b = (b - 0.5) * contrast + 0.5;

      // Apply saturation
      const gray = 0.299 * r + 0.587 * g + 0.114 * b;
      r = gray + saturation * (r - gray);
      g = gray + saturation * (g - gray);
      b = gray + saturation * (b - gray);

      // Convert back to 0-255 range and clamp
      data[i] = Math.max(0, Math.min(255, Math.round(r * 255)));
      data[i + 1] = Math.max(0, Math.min(255, Math.round(g * 255)));
      data[i + 2] = Math.max(0, Math.min(255, Math.round(b * 255)));
    }

    this.ctx.putImageData(imageData, 0, 0);
  }

  /**
   * Pas transparantie toe
   */
  applyTransparency({ color = null, tolerance = 10, removeBackground = false }) {
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const data = imageData.data;

    if (color) {
      // Maak specifieke kleur transparant
      const targetColor = this.hexToRgb(color);
      
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];

        // Check if color matches within tolerance
        const distance = Math.sqrt(
          Math.pow(r - targetColor.r, 2) +
          Math.pow(g - targetColor.g, 2) +
          Math.pow(b - targetColor.b, 2)
        );

        if (distance <= tolerance) {
          data[i + 3] = 0; // Set alpha to 0 (transparent)
        }
      }
    }

    if (removeBackground) {
      // Simpele achtergrond verwijdering (hoeken transparant maken)
      this.removeCornerBackground(data, tolerance);
    }

    this.ctx.putImageData(imageData, 0, 0);
  }

  /**
   * Verwijder achtergrond op basis van hoekpixels
   */
  removeCornerBackground(data, tolerance) {
    const width = this.canvas.width;
    const height = this.canvas.height;
    
    // Neem gemiddelde kleur van alle 4 hoeken
    const corners = [
      [0, 0], // linksboven
      [(width - 1) * 4, 0], // rechtsboven  
      [0, (height - 1) * width * 4], // linksonder
      [(width - 1) * 4, (height - 1) * width * 4] // rechtsonder
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
        data[i + 3] = 0; // Transparant maken
      }
    }
  }

  /**
   * Converteer hex kleur naar RGB
   */
  hexToRgb(hex) {
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
  canvasToBlob(format, quality) {
    return new Promise((resolve) => {
      const mimeType = format === 'jpeg' ? 'image/jpeg' : 'image/png';
      this.canvas.toBlob(resolve, mimeType, quality);
    });
  }

  /**
   * Download processed image
   */
  async downloadImage(blob, filename = 'processed-image.jpg') {
    // Sanitize filename to prevent XSS
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

// Convenience functie voor eenvoudig gebruik
export const processImage = async (imageInput, options) => {
  const processor = new ImageProcessor();
  return await processor.processImage(imageInput, options);
};

// Voorbeeld gebruik:
/*
const options = {
  resize: { width: 800, height: 600 },
  crop: { x: 100, y: 50, width: 400, height: 300 },
  transparency: { color: '#ffffff', tolerance: 20 },
  colorAdjust: { brightness: 1.2, saturation: 1.3, contrast: 1.1 },
  outputFormat: 'png',
  quality: 0.9
};

const processedBlob = await processImage(file, options);
*/