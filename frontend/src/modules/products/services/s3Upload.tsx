import { S3Client, PutObjectCommand, ListObjectsV2Command, DeleteObjectsCommand } from '@aws-sdk/client-s3';
import { Product as BaseProduct } from '../../../types';

interface ProductWithImage extends BaseProduct {
  image?: string | string[];
}

// Configure AWS SDK v3
const s3Client = new S3Client({
  region: process.env.REACT_APP_AWS_REGION || 'eu-west-1',
  credentials: {
    accessKeyId: process.env.REACT_APP_AWS_ACCESS_KEY_ID || '',
    secretAccessKey: process.env.REACT_APP_AWS_SECRET_ACCESS_KEY || ''
  }
});

export const uploadToS3 = async (
  file: File, 
  bucketName: string = process.env.REACT_APP_S3_BUCKET || 'my-hdcn-bucket'
): Promise<string> => {
  const fileName = `product-images/${Date.now()}-${file.name}`;
  
  console.log('Using bucket:', bucketName);
  
  const command = new PutObjectCommand({
    Bucket: bucketName,
    Key: fileName,
    Body: file,
    ContentType: file.type
  });

  try {
    await s3Client.send(command);
    // Construct the URL manually since v3 doesn't return Location by default
    const region = process.env.REACT_APP_AWS_REGION || 'eu-west-1';
    const url = `https://${bucketName}.s3.${region}.amazonaws.com/${fileName}`;
    return url;
  } catch (error) {
    console.error('S3 upload error:', error);
    throw error;
  }
};

export const cleanupUnusedImages = async (
  products: ProductWithImage[], 
  bucketName: string = process.env.REACT_APP_S3_BUCKET || 'my-hdcn-bucket'
): Promise<number> => {
  try {
    const listCommand = new ListObjectsV2Command({
      Bucket: bucketName,
      Prefix: 'product-images/'
    });
    
    const s3Objects = await s3Client.send(listCommand);
    const s3ImageKeys = s3Objects.Contents?.map(obj => obj.Key).filter(Boolean) || [];
    
    const usedImageUrls: string[] = [];
    
    products.forEach(p => {
      if (p.image) {
        const images = Array.isArray(p.image) ? p.image : [p.image];
        
        images.forEach(imageUrl => {
          if (imageUrl && imageUrl.includes('product-images/')) {
            const url = new URL(imageUrl);
            usedImageUrls.push(url.pathname.substring(1));
          }
        });
      }
    });
    
    const unusedImages = s3ImageKeys.filter(key => key && !usedImageUrls.includes(key));
    
    console.log(`Found ${unusedImages.length} unused images to delete:`, unusedImages);
    
    if (unusedImages.length > 0) {
      const deleteCommand = new DeleteObjectsCommand({
        Bucket: bucketName,
        Delete: {
          Objects: unusedImages.map(key => ({ Key: key }))
        }
      });
      
      const result = await s3Client.send(deleteCommand);
      console.log('Deleted unused images:', result.Deleted);
      return result.Deleted?.length || 0;
    }
    
    return 0;
  } catch (error) {
    console.error('Cleanup error:', error);
    throw error;
  }
};