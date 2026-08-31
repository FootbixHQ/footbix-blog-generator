#!/usr/bin/env python3
"""
Test script to validate credentials for Shopify, Figma, and other services
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_shopify_credentials():
    """Test Shopify API credentials"""
    print("\n🔍 Testing Shopify Credentials...")
    print("-" * 50)
    
    store_url = os.getenv('SHOPIFY_STORE_URL')
    access_token = os.getenv('SHOPIFY_ADMIN_API_TOKEN')
    api_version = os.getenv('SHOPIFY_API_VERSION', '2024-01')
    
    if not store_url or not access_token:
        print("❌ Missing Shopify credentials")
        print(f"   SHOPIFY_STORE_URL: {'✓' if store_url else '✗'}")
        print(f"   SHOPIFY_ADMIN_API_TOKEN: {'✓' if access_token else '✗'}")
        return False
    
    try:
        headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        # Test API connection with a simple query
        url = f"{store_url}/admin/api/{api_version}/graphql.json"
        query = '''
        {
          shop {
            name
            url
          }
        }
        '''
        
        response = requests.post(url, json={'query': query}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'shop' in data['data']:
                shop_name = data['data']['shop']['name']
                print(f"✅ Shopify Connected Successfully!")
                print(f"   Store: {shop_name}")
                print(f"   URL: {data['data']['shop']['url']}")
                return True
            elif 'errors' in data:
                print(f"❌ Shopify API Error: {data['errors']}")
                return False
        else:
            print(f"❌ Shopify API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Shopify connection timeout")
        return False
    except Exception as e:
        print(f"❌ Shopify connection error: {str(e)}")
        return False


def test_figma_credentials():
    """Test Figma API credentials"""
    print("\n🔍 Testing Figma Credentials...")
    print("-" * 50)
    
    api_token = os.getenv('FIGMA_API_TOKEN')
    file_id = os.getenv('FIGMA_FILE_ID')
    
    if not api_token or not file_id:
        print("❌ Missing Figma credentials")
        print(f"   FIGMA_API_TOKEN: {'✓' if api_token else '✗'}")
        print(f"   FIGMA_FILE_ID: {'✓' if file_id else '✗'}")
        return False
    
    try:
        headers = {'X-FIGMA-TOKEN': api_token}
        url = f"https://api.figma.com/v1/files/{file_id}"
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Figma Connected Successfully!")
            print(f"   File: {data.get('name', 'Unknown')}")
            print(f"   Last Updated: {data.get('lastModified', 'Unknown')}")
            return True
        elif response.status_code == 401:
            print(f"❌ Figma Authentication Failed (401 Unauthorized)")
            return False
        elif response.status_code == 404:
            print(f"❌ Figma File Not Found (404)")
            return False
        else:
            print(f"❌ Figma API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Figma connection timeout")
        return False
    except Exception as e:
        print(f"❌ Figma connection error: {str(e)}")
        return False


def test_environment_setup():
    """Test general environment setup"""
    print("\n🔍 Testing Environment Setup...")
    print("-" * 50)
    
    required_vars = {
        'SHOPIFY_STORE_URL': 'Shopify Store URL',
        'SHOPIFY_ADMIN_API_TOKEN': 'Shopify API Token',
        'SHOPIFY_API_VERSION': 'Shopify API Version',
        'FIGMA_API_TOKEN': 'Figma API Token',
        'FIGMA_FILE_ID': 'Figma File ID',
    }
    
    optional_vars = {
        'BLOG_TEMPLATE_ID': 'Blog Template ID',
        'MAX_UPLOAD_SIZE_MB': 'Max Upload Size (MB)',
        'TEMP_IMAGE_DIR': 'Temp Image Directory',
    }
    
    all_ok = True
    
    print("Required Variables:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        status = '✓' if value else '✗'
        print(f"  {status} {desc}: {var}")
        if not value:
            all_ok = False
    
    print("\nOptional Variables:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        status = '✓' if value else '·'
        print(f"  {status} {desc}: {var} = {value or '(not set)'}")
    
    return all_ok


def test_directories():
    """Test if required directories can be created"""
    print("\n🔍 Testing Directory Setup...")
    print("-" * 50)
    
    directories = [
        'uploads',
        os.getenv('TEMP_IMAGE_DIR', './temp_images'),
    ]
    
    all_ok = True
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✓ {directory}: accessible/created")
        except Exception as e:
            print(f"✗ {directory}: {str(e)}")
            all_ok = False
    
    return all_ok


def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("🧪 Footbix Blog Generator - Credentials Test")
    print("=" * 50)
    
    results = {
        'Environment Setup': test_environment_setup(),
        'Directories': test_directories(),
        'Shopify API': test_shopify_credentials(),
        'Figma API': test_figma_credentials(),
    }
    
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All tests passed! Ready to use.")
        return 0
    else:
        print("❌ Some tests failed. Please check your credentials.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
