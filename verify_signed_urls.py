import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path so we can import from 'api'
sys.path.append(r"c:\Users\neilc\OneDrive\Documents\GitHub\snipshot-desktop")

load_dotenv(r"c:\Users\neilc\OneDrive\Documents\GitHub\snipshot-desktop\.env")

from api.supabase_client import SupabaseAPIClient

def main():
    print("Initializing SupabaseAPIClient...")
    try:
        client = SupabaseAPIClient()
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        return

    print("Checking active session / is_authenticated...")
    print(f"Authenticated: {client.is_authenticated}")
    if client.user:
        print(f"User email: {client.user.email}")
        print(f"User ID: {client.user.id}")
    else:
        print("No active user session.")

    # Test signed URL helpers exist
    print(f"Has _get_signed_url: {hasattr(client, '_get_signed_url')}")
    print(f"Has _get_signed_urls: {hasattr(client, '_get_signed_urls')}")
    print(f"Has _sign_single_image_url: {hasattr(client, '_sign_single_image_url')}")
    print(f"Has _sign_image_urls: {hasattr(client, '_sign_image_urls')}")

    # Mock a data dict
    img = {
        "id": 123,
        "storage_path": "test/path.png",
        "public_url": "original_public_url"
    }
    
    print("Testing _sign_single_image_url (expecting fallback to empty string if unauthenticated):")
    signed_img = client._sign_single_image_url(img.copy(), expires_in=3600)
    print("Signed img:", signed_img)

    # Test list helper
    imgs = [
        {"id": 1, "storage_path": "test/path1.png"},
        {"id": 2, "storage_path": "test/path2.png"}
    ]
    print("Testing _sign_image_urls:")
    signed_imgs = client._sign_image_urls(imgs.copy(), expires_in=3600)
    print("Signed imgs:", signed_imgs)

if __name__ == "__main__":
    main()
