#!/usr/bin/env python3
"""
Test script to measure API performance
"""
import time
from api.client import APIClient

def test_api_performance():
    print('Testing API performance...')
    client = APIClient()

    # Test folders API
    print('Testing folders API...')
    start = time.time()
    result = client.get_folders()
    end = time.time()
    print(f'Folders API call took: {end - start:.2f} seconds')
    print(f'Success: {result["success"]}')

    if result['success']:
        folders = result['data'].get('folders', [])
        print(f'Found {len(folders)} folders')

        # Test images API
        print('Testing images API...')
        start = time.time()
        images_result = client.get_images(folder_id=0, per_page=20)
        end = time.time()
        print(f'Images API call took: {end - start:.2f} seconds')
        print(f'Success: {images_result["success"]}')

        if images_result['success']:
            images = images_result['data'].get('images', [])
            print(f'Found {len(images)} images')

if __name__ == '__main__':
    test_api_performance()