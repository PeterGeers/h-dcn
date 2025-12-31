# Create Simple Placeholder Images
# Generates basic placeholder images for all missing product images

# Bypass "more" prompts for long outputs
$env:AWS_PAGER = ""

Write-Host "🖼️ Creating placeholder images for missing products..." -ForegroundColor Yellow

# List of product images that need to be created
$productImages = @(
    "BS-U", "DA-D", "DA-H", "DB-D", "DB-H", 
    "G1", "G2", "G3", "G4", "G8", "G9", "G10", "G12", "G13", "G15",
    "RC-H", "SD", "SH", "TD", "TD-60", "TH", "TH-60", "TH-65"
)

# Create a temporary directory for placeholders
$tempDir = "temp-placeholders"
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "📁 Created temporary directory: $tempDir" -ForegroundColor Cyan

# Create simple HTML file to generate placeholders using canvas
$htmlContent = @"
<!DOCTYPE html>
<html>
<head>
    <title>Placeholder Generator</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        canvas { border: 1px solid #ccc; margin: 10px; }
        .product { display: inline-block; margin: 10px; text-align: center; }
    </style>
</head>
<body>
    <h1>H-DCN Product Placeholder Generator</h1>
    <div id="placeholders"></div>
    
    <script>
        const products = ['BS-U', 'DA-D', 'DA-H', 'DB-D', 'DB-H', 'G1', 'G2', 'G3', 'G4', 'G8', 'G9', 'G10', 'G12', 'G13', 'G15', 'RC-H', 'SD', 'SH', 'TD', 'TD-60', 'TH', 'TH-60', 'TH-65'];
        
        function createPlaceholder(productId) {
            const canvas = document.createElement('canvas');
            canvas.width = 400;
            canvas.height = 400;
            const ctx = canvas.getContext('2d');
            
            // Background
            ctx.fillStyle = '#f8f9fa';
            ctx.fillRect(0, 0, 400, 400);
            
            // Border
            ctx.strokeStyle = '#dee2e6';
            ctx.lineWidth = 2;
            ctx.strokeRect(10, 10, 380, 380);
            
            // H-DCN Logo area
            ctx.fillStyle = '#ff6600';
            ctx.fillRect(50, 50, 300, 80);
            
            // H-DCN Text
            ctx.fillStyle = 'white';
            ctx.font = 'bold 36px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('H-DCN', 200, 105);
            
            // Product ID
            ctx.fillStyle = '#333333';
            ctx.font = 'bold 48px Arial';
            ctx.fillText(productId, 200, 200);
            
            // Product text
            ctx.fillStyle = '#666666';
            ctx.font = '24px Arial';
            ctx.fillText('Product', 200, 250);
            ctx.fillText('Afbeelding', 200, 280);
            ctx.fillText('Binnenkort', 200, 320);
            
            return canvas;
        }
        
        function downloadCanvas(canvas, filename) {
            const link = document.createElement('a');
            link.download = filename;
            link.href = canvas.toDataURL('image/jpeg', 0.8);
            link.click();
        }
        
        const container = document.getElementById('placeholders');
        
        products.forEach(productId => {
            const div = document.createElement('div');
            div.className = 'product';
            
            const canvas = createPlaceholder(productId);
            div.appendChild(canvas);
            
            const button = document.createElement('button');
            button.textContent = 'Download ' + productId + '.jpg';
            button.onclick = () => downloadCanvas(canvas, productId + '.jpg');
            div.appendChild(document.createElement('br'));
            div.appendChild(button);
            
            container.appendChild(div);
        });
        
        // Auto-download all
        const downloadAllBtn = document.createElement('button');
        downloadAllBtn.textContent = 'Download All Placeholders';
        downloadAllBtn.style.cssText = 'font-size: 18px; padding: 10px 20px; margin: 20px; background: #ff6600; color: white; border: none; border-radius: 5px;';
        downloadAllBtn.onclick = () => {
            products.forEach((productId, index) => {
                setTimeout(() => {
                    const canvas = createPlaceholder(productId);
                    downloadCanvas(canvas, productId + '.jpg');
                }, index * 500); // Delay to avoid browser blocking
            });
        };
        document.body.insertBefore(downloadAllBtn, container);
    </script>
</body>
</html>
"@

# Save HTML file
$htmlFile = "$tempDir/placeholder-generator.html"
$htmlContent | Out-File -FilePath $htmlFile -Encoding UTF8

Write-Host "📄 Created placeholder generator: $htmlFile" -ForegroundColor Green
Write-Host ""
Write-Host "🔧 MANUAL STEPS REQUIRED:" -ForegroundColor Red
Write-Host "1. Open the HTML file in a web browser:" -ForegroundColor Yellow
Write-Host "   $((Get-Location).Path)\$htmlFile" -ForegroundColor White
Write-Host "2. Click 'Download All Placeholders' button" -ForegroundColor Yellow
Write-Host "3. Save all images to the temp-placeholders folder" -ForegroundColor Yellow
Write-Host "4. Run the upload script to deploy them to S3" -ForegroundColor Yellow
Write-Host ""
Write-Host "📋 Alternative: Use any image editing software to create 400x400 images with:" -ForegroundColor Cyan
Write-Host "   - Product ID as main text" -ForegroundColor Gray
Write-Host "   - H-DCN branding" -ForegroundColor Gray
Write-Host "   - Save as [ProductID].jpg" -ForegroundColor Gray
Write-Host ""
Write-Host "🚀 After creating images, upload with:" -ForegroundColor Green
Write-Host "   aws s3 sync temp-placeholders/ s3://my-hdcn-bucket/product-images/ --exclude '*.html'" -ForegroundColor White