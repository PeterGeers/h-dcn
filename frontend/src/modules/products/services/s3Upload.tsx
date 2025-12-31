import { Product as BaseProduct } from '../../../types';

interface ProductWithImage extends BaseProduct {
  image?: string | string[];
}

export const uploadToS3 = async (
  file: File, 
  productId?: string,
  bucketName?: string
): Promise<string> => {
  // Use provided bucket name or default to my-hdcn-bucket
  const targetBucket = bucketName || 'my-hdcn-bucket';
  
  // Use logical naming: if productId provided, use it; otherwise use timestamp
  let fileName: string;
  
  if (productId) {
    // For existing products, use the product ID as filename
    const fileExtension = file.name.split('.').pop() || 'jpg';
    fileName = `product-images/${productId}.${fileExtension}`;
  } else {
    // For new products without ID, use timestamp (will be updated later)
    fileName = `product-images/${Date.now()}-${file.name}`;
  }
  
  try {
    // Convert File to base64 for API upload
    const fileBuffer = await file.arrayBuffer();
    const uint8Array = new Uint8Array(fileBuffer);
    const base64String = btoa(String.fromCharCode(...uint8Array));
    
    // Get enhanced groups from localStorage for authentication
    const storedUser = localStorage.getItem('hdcn_auth_user');
    let enhancedGroups = ['hdcnAdmins', 'Products_CRUD_All']; // fallback with multiple roles
    let authToken = '';
    
    console.log('🔍 DEBUG: Raw stored user data:', storedUser);
    
    if (storedUser) {
      try {
        const user = JSON.parse(storedUser);
        
        // Extract JWT token for Authorization header
        const jwtToken = user.signInUserSession?.accessToken?.jwtToken;
        if (jwtToken) {
          authToken = jwtToken;
        }
        
        const groups = user.signInUserSession?.accessToken?.payload?.['cognito:groups'];
        
        if (groups && Array.isArray(groups)) {
          enhancedGroups = groups;
        }
      } catch (error) {
        // Use fallback groups on parse error
      }
    }
    
    // Upload via secure backend API
    const apiUrl = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/s3/files';
    
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Enhanced-Groups': JSON.stringify(enhancedGroups)
    };
    
    // Add Authorization header if we have a token
    if (authToken) {
      requestHeaders['Authorization'] = `Bearer ${authToken}`;
      console.log('✅ DEBUG: Added Authorization header');
    } else {
      console.log('⚠️ DEBUG: No auth token available - request may fail');
    }
    
    const requestBody = {
      bucketName: targetBucket,
      fileKey: fileName,
      fileData: base64String,
      contentType: file.type,
      cacheControl: 'public, max-age=31536000' // Cache images for 1 year
    };
    
    console.log('🚀 DEBUG: Making API request to:', apiUrl);
    console.log('🚀 DEBUG: Request headers:', requestHeaders);
    console.log('🚀 DEBUG: Request body keys:', Object.keys(requestBody));
    console.log('🚀 DEBUG: File info:', {
      name: file.name,
      type: file.type,
      size: file.size,
      targetBucket,
      fileName
    });
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: requestHeaders,
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `Upload failed: ${response.status}`);
    }
    
    const result = await response.json();
    
    return result.fileUrl;
    
  } catch (error) {
    throw error;
  }
};

// Helper function to generate logical image URL for a product
export const getLogicalImageUrl = (
  productId: string, 
  fileExtension: string = 'jpg',
  bucketName?: string
): string => {
  // Use provided bucket name or default to my-hdcn-bucket
  const targetBucket = bucketName || 'my-hdcn-bucket';
  
  const region = 'eu-west-1';
  return `https://${targetBucket}.s3.${region}.amazonaws.com/product-images/${productId}.${fileExtension}`;
};

export const cleanupUnusedImages = async (
  products: ProductWithImage[], 
  bucketName?: string
): Promise<number> => {
  // Use provided bucket name or default to my-hdcn-bucket
  const targetBucket = bucketName || 'my-hdcn-bucket';
  
  try {
    // Get enhanced groups from localStorage for authentication
    const storedUser = localStorage.getItem('hdcn_auth_user');
    let enhancedGroups = ['hdcnAdmins']; // fallback
    let authToken = '';
    
    if (storedUser) {
      const user = JSON.parse(storedUser);
      
      // Extract JWT token for Authorization header
      const jwtToken = user.signInUserSession?.accessToken?.jwtToken;
      if (jwtToken) {
        authToken = jwtToken;
      }
      
      const groups = user.signInUserSession?.accessToken?.payload?.['cognito:groups'];
      if (groups && Array.isArray(groups)) {
        enhancedGroups = groups;
      }
    }
    
    // List all files in product-images folder via secure API
    const apiUrl = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/s3/files';
    const listUrl = `${apiUrl}?bucketName=${targetBucket}&prefix=product-images/&recursive=true`;
    
    const listHeaders: Record<string, string> = {
      'X-Enhanced-Groups': JSON.stringify(enhancedGroups)
    };
    
    if (authToken) {
      listHeaders['Authorization'] = `Bearer ${authToken}`;
    }
    
    const listResponse = await fetch(listUrl, {
      method: 'GET',
      headers: listHeaders
    });
    
    if (!listResponse.ok) {
      throw new Error(`Failed to list images: ${listResponse.status}`);
    }
    
    const listResult = await listResponse.json();
    const s3ImageKeys = listResult.files?.map((file: any) => file.key) || [];
    
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
    
    const unusedImages = s3ImageKeys.filter((key: string) => key && !usedImageUrls.includes(key));
    
    if (unusedImages.length > 0) {
      // Delete unused images via secure API
      let deletedCount = 0;
      
      for (const imageKey of unusedImages) {
        try {
          const deleteHeaders: Record<string, string> = {
            'Content-Type': 'application/json',
            'X-Enhanced-Groups': JSON.stringify(enhancedGroups)
          };
          
          if (authToken) {
            deleteHeaders['Authorization'] = `Bearer ${authToken}`;
          }
          
          const deleteResponse = await fetch(apiUrl, {
            method: 'DELETE',
            headers: deleteHeaders,
            body: JSON.stringify({
              bucketName: targetBucket,
              fileKey: imageKey
            })
          });
          
          if (deleteResponse.ok) {
            deletedCount++;
          }
        } catch (error) {
          // Continue with other deletions
        }
      }
      
      return deletedCount;
    }
    
    return 0;
  } catch (error) {
    throw error;
  }
};