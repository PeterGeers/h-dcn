"""Upload club logos to the frontend S3 bucket."""
import boto3
import os
import glob

PROFILE = 'nonprofit-deploy'
REGION = 'eu-west-1'
BUCKET = 'h-dcn-frontend-506221081911'
S3_PREFIX = 'assets/presmeet/logos/'
LOGOS_DIR = os.path.join(os.path.dirname(__file__), '..', '.kiro', 'specs', 'presmeet-v2', 'seed', 'club_logos')

session = boto3.Session(profile_name=PROFILE, region_name=REGION)
s3 = session.client('s3')

logos = glob.glob(os.path.join(LOGOS_DIR, 'cl*.png'))
print(f"Found {len(logos)} logos to upload")

for filepath in sorted(logos):
    filename = os.path.basename(filepath)
    # cl1.png -> 1.png, cl10.png -> 10.png
    s3_key = S3_PREFIX + filename.replace('cl', '')
    
    s3.upload_file(
        filepath,
        BUCKET,
        s3_key,
        ExtraArgs={
            'ContentType': 'image/png',
            'CacheControl': 'public, max-age=86400',
        }
    )
    print(f"  Uploaded {filename} -> s3://{BUCKET}/{s3_key}")

print(f"\nDone. All {len(logos)} logos uploaded to s3://{BUCKET}/{S3_PREFIX}")
