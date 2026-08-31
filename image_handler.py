import os
import requests
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class ShopifyMediaHandler:
    """Handles image uploads to Shopify Media Library"""

    def __init__(self):
        self.store_url = os.getenv('SHOPIFY_STORE_URL')
        self.access_token = os.getenv('SHOPIFY_ADMIN_API_TOKEN')
        self.api_version = os.getenv('SHOPIFY_API_VERSION', '2024-01')
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }

    def upload_image(self, file_path: str, alt_text: str = "") -> Optional[Dict]:
        """Upload image to Shopify Media Library"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                headers = {'X-Shopify-Access-Token': self.access_token}

                url = f"{self.store_url}/admin/api/{self.api_version}/graphql.json"

                # Use GraphQL to upload
                mutation = """
                mutation {
                  stagedUploadsCreate(input: {
                    resource: PRODUCT_IMAGE
                    filename: "%s"
                  }) {
                    stagedTargets {
                      resourceUrl
                      url
                      parameters {
                        name
                        value
                      }
                    }
                  }
                }
                """ % Path(file_path).name

                response = requests.post(url, json={'query': mutation}, headers=headers)
                return response.json()
        except Exception as e:
            print(f"Error uploading to Shopify: {e}")
            return None

    def get_media_library_url(self, file_path: str) -> Optional[str]:
        """Get media URL after upload"""
        try:
            response = self.upload_image(file_path)
            if response and 'data' in response:
                return response['data'].get('resourceUrl')
        except Exception as e:
            print(f"Error getting media URL: {e}")
        return None


class FigmaImageGenerator:
    """Generates images from Figma templates"""

    def __init__(self):
        self.api_token = os.getenv('FIGMA_API_TOKEN')
        self.file_id = os.getenv('FIGMA_FILE_ID')
        self.headers = {'X-FIGMA-TOKEN': self.api_token}

    def get_template_nodes(self) -> List[Dict]:
        """Get all template nodes from Figma file"""
        try:
            url = f"https://api.figma.com/v1/files/{self.file_id}"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                return self._extract_exportable_nodes(data['document'])
            else:
                print(f"Error fetching Figma file: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting template nodes: {e}")
            return []

    def _extract_exportable_nodes(self, node: Dict, nodes: List[Dict] = None) -> List[Dict]:
        """Recursively extract nodes marked for export"""
        if nodes is None:
            nodes = []

        if 'children' in node:
            for child in node['children']:
                # Look for nodes with "export" in name or properties
                if 'name' in child and 'export' in child['name'].lower():
                    nodes.append(child)
                self._extract_exportable_nodes(child, nodes)

        return nodes

    def export_node_as_image(self, node_id: str, format: str = 'png') -> Optional[str]:
        """Export a single Figma node as image"""
        try:
            url = f"https://api.figma.com/v1/images/{self.file_id}"
            params = {
                'ids': node_id,
                'format': format,
                'scale': 2  # 2x for better quality
            }

            response = requests.get(url, params=params, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                if 'images' in data and node_id in data['images']:
                    return data['images'][node_id]
            else:
                print(f"Error exporting node: {response.status_code}")
        except Exception as e:
            print(f"Error exporting Figma node: {e}")

        return None

    def download_image(self, url: str, output_path: str) -> bool:
        """Download image from Figma export URL"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            print(f"Error downloading image: {e}")
        return False

    def generate_blog_images(self, blog_topic: str, product_names: List[str]) -> List[str]:
        """Generate a set of images for the blog post"""
        generated_images = []

        try:
            # Get available templates
            templates = self.get_template_nodes()

            if not templates:
                print("No exportable templates found in Figma")
                return []

            # Export each template
            temp_dir = os.getenv('TEMP_IMAGE_DIR', './temp_images')
            os.makedirs(temp_dir, exist_ok=True)

            for i, template in enumerate(templates[:3]):  # Limit to 3 images
                node_id = template.get('id')
                if node_id:
                    image_url = self.export_node_as_image(node_id)
                    if image_url:
                        output_path = f"{temp_dir}/blog_image_{i}.png"
                        if self.download_image(image_url, output_path):
                            generated_images.append(output_path)

        except Exception as e:
            print(f"Error generating blog images: {e}")

        return generated_images


class BlogImageOrchestrator:
    """Orchestrates the entire image workflow"""

    def __init__(self):
        self.shopify_handler = ShopifyMediaHandler()
        self.figma_generator = FigmaImageGenerator()

    def process_blog_images(self,
                           user_images: List[str],
                           blog_topic: str,
                           product_names: List[str]) -> Dict:
        """
        Process both user-uploaded and auto-generated images

        Returns:
        {
            'user_images': [{'url': '...', 'type': 'user_uploaded'}],
            'generated_images': [{'url': '...', 'type': 'auto_generated'}],
            'all_images': [...]
        }
        """
        result = {
            'user_images': [],
            'generated_images': [],
            'all_images': []
        }

        try:
            # Process user-uploaded images
            for user_image in user_images:
                # Upload to Shopify
                shopify_url = self.shopify_handler.get_media_library_url(user_image)
                if shopify_url:
                    result['user_images'].append({
                        'url': shopify_url,
                        'type': 'user_uploaded',
                        'filename': Path(user_image).name
                    })

            # Generate images from Figma
            generated_paths = self.figma_generator.generate_blog_images(
                blog_topic,
                product_names
            )

            for gen_image in generated_paths:
                # Upload generated images to Shopify too
                shopify_url = self.shopify_handler.get_media_library_url(gen_image)
                if shopify_url:
                    result['generated_images'].append({
                        'url': shopify_url,
                        'type': 'auto_generated',
                        'filename': Path(gen_image).name
                    })

            # Combine all images
            result['all_images'] = result['user_images'] + result['generated_images']

        except Exception as e:
            print(f"Error processing blog images: {e}")

        return result
