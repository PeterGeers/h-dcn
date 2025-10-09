import AWS from 'aws-sdk';

// Configure AWS (je moet deze waarden aanpassen naar jouw AWS setup)
AWS.config.update({
  accessKeyId: process.env.REACT_APP_AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.REACT_APP_AWS_SECRET_ACCESS_KEY,
  region: process.env.REACT_APP_AWS_REGION || 'eu-west-1'
});

const s3 = new AWS.S3();

export const uploadToS3 = async (file, bucketName = process.env.REACT_APP_S3_BUCKET || 'my-hdcn-bucket') => {
  const fileName = `product-images/${Date.now()}-${file.name}`;
  
  console.log('Using bucket:', bucketName);
  
  const params = {
    Bucket: bucketName,
    Key: fileName,
    Body: file,
    ContentType: file.type
  };

  try {
    const result = await s3.upload(params).promise();
    return result.Location; // Retourneert de publieke URL
  } catch (error) {
    console.error('S3 upload error:', error);
    throw error;
  }
};

export const cleanupUnusedImages = async (products, bucketName = process.env.REACT_APP_S3_BUCKET || 'my-hdcn-bucket') => {
  try {
    // Get all images from S3 product-images folder
    const listParams = {
      Bucket: bucketName,
      Prefix: 'product-images/'
    };
    
    const s3Objects = await s3.listObjectsV2(listParams).promise();
    const s3ImageKeys = s3Objects.Contents.map(obj => obj.Key);
    
    // Get all image URLs used in products
    const usedImageUrls = [];
    
    products.forEach(p => {
      if (p.image) {
        // Handle both string and array formats
        const images = Array.isArray(p.image) ? p.image : [p.image];
        
        images.forEach(imageUrl => {
          if (imageUrl && imageUrl.includes('product-images/')) {
            const url = new URL(imageUrl);
            usedImageUrls.push(url.pathname.substring(1)); // Remove leading slash
          }
        });
      }
    });
    
    // Find unused images
    const unusedImages = s3ImageKeys.filter(key => !usedImageUrls.includes(key));
    
    console.log(`Found ${unusedImages.length} unused images to delete:`, unusedImages);
    
    // Delete unused images
    if (unusedImages.length > 0) {
      const deleteParams = {
        Bucket: bucketName,
        Delete: {
          Objects: unusedImages.map(key => ({ Key: key }))
        }
      };
      
      const result = await s3.deleteObjects(deleteParams).promise();
      console.log('Deleted unused images:', result.Deleted);
      return result.Deleted.length;
    }
    
    return 0;
  } catch (error) {
    console.error('Cleanup error:', error);
    throw error;
  }
};