import AWS from 'aws-sdk';
import { Product as BaseProduct } from '../../../types';

interface ProductWithImage extends BaseProduct {
  image?: string | string[];
}

// Configure AWS
AWS.config.update({
  accessKeyId: process.env.REACT_APP_AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.REACT_APP_AWS_SECRET_ACCESS_KEY,
  region: process.env.REACT_APP_AWS_REGION || 'eu-west-1'
});

const s3 = new AWS.S3();

export const uploadToS3 = async (
  file: File, 
  bucketName: string = process.env.REACT_APP_S3_BUCKET || 'my-hdcn-bucket'
): Promise<string> => {
  const fileName = `product-images/${Date.now()}-${file.name}`;
  
  console.log('Using bucket:', bucketName);
  
  const params: AWS.S3.PutObjectRequest = {
    Bucket: bucketName,
    Key: fileName,
    Body: file,
    ContentType: file.type
  };

  try {
    const result = await s3.upload(params).promise();
    return result.Location;
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
    const listParams: AWS.S3.ListObjectsV2Request = {
      Bucket: bucketName,
      Prefix: 'product-images/'
    };
    
    const s3Objects = await s3.listObjectsV2(listParams).promise();
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
      const deleteParams: AWS.S3.DeleteObjectsRequest = {
        Bucket: bucketName,
        Delete: {
          Objects: unusedImages.map(key => ({ Key: key }))
        }
      };
      
      const result = await s3.deleteObjects(deleteParams).promise();
      console.log('Deleted unused images:', result.Deleted);
      return result.Deleted?.length || 0;
    }
    
    return 0;
  } catch (error) {
    console.error('Cleanup error:', error);
    throw error;
  }
};