export const getLogoBase64 = async (): Promise<string> => {
  try {
    const bucketUrl = process.env.REACT_APP_LOGO_BUCKET_URL;
    
    if (!bucketUrl) {
      throw new Error('Logo bucket URL not configured');
    }
    
    const response = await fetch(`${bucketUrl}/imagesWebsite/hdcnFavico.png`);
    const blob = await response.blob();
    
    return new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.readAsDataURL(blob);
    });
  } catch (error) {
    console.error('Failed to load logo:', error);
    const svgLogo = `
      <svg width="60" height="60" xmlns="http://www.w3.org/2000/svg">
        <rect width="60" height="60" fill="#FF6B35"/>
        <text x="30" y="35" font-family="Arial" font-size="12" font-weight="bold" text-anchor="middle" fill="white">H-DCN</text>
      </svg>
    `;
    const base64 = btoa(svgLogo);
    return `data:image/svg+xml;base64,${base64}`;
  }
};

export const FALLBACK_LOGO_BASE64: string = 'data:image/svg+xml;base64,CiAgICAgIDxzdmcgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogICAgICAgIDxyZWN0IHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgZmlsbD0iI0ZGNkIzNSIvPgogICAgICAgIDx0ZXh0IHg9IjMwIiB5PSIzNSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iYm9sZCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0id2hpdGUiPkgtRENOPC90ZXh0PgogICAgICA8L3N2Zz4KICAgICA=';