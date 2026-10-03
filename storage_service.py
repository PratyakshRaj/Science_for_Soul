import os
import aioboto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

# Cloudflare R2 Credentials (Uses fallback dummy values if missing from .env)
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "dummy_account_id")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "dummy_access_key")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "dummy_secret_key")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "student-assets")

# Construct custom endpoint required by Cloudflare R2 API architecture
R2_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Force path-style routing to comply with R2 structural requirements
s3_config = Config(s3={'addressing_style': 'path'})

async def generate_secure_expiry_url(asset_path: str) -> str:
    """
    Accepts a relative asset path (e.g., 'courses/vectors/cross_product.mp4')
    and returns a secured, tokenized URL that expires in exactly 60 minutes.
    """
    session = aioboto3.Session()
    
    async with session.client(
        's3',
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=s3_config
    ) as s3_client:
        
        presigned_url = await s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': R2_BUCKET_NAME,
                'Key': asset_path
            },
            ExpiresIn=3600  # Strict 60-minute duration window specified by architecture
        )
        
        return presigned_url
