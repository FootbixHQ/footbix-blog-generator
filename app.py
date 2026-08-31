from flask import Flask, render_template, request, jsonify
import requests
import os
import json
from image_routes import images_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(images_bp)

# Only need ONE key now


# --- DataForSEO via Composio ---
def research_keywords(keyword):
    login = os.getenv('DATAFORSEO_LOGIN')
    pwd = os.getenv('DATAFORSEO_PASSWORD')
    if not login or not pwd:
        return {'status': 'success', 'search_volume': 500, 'competition': 'MEDIUM', 'cpc': 2.0}
    try:
        url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"
        r = requests.post(url, json=[{"keywords": [keyword]}], auth=(login, pwd), timeout=10)
        if r.status_code == 200:
            res = r.json().get('tasks', [{}])[0].get('result', [{}])[0]
            return {'status': 'success', 'search_volume': res.get('search_volume', 0), 'competition': res.get('competition', 'MEDIUM'), 'cpc': res.get('cpc', 0)}
        return {'status': 'success', 'search_volume': 500, 'competition': 'MEDIUM', 'cpc': 2.0}
    except:
        return {'status': 'success', 'search_volume': 500, 'competition': 'MEDIUM', 'cpc': 2.0}

# --- Generate Metadata ---
def generate_metadata(topic, products):
    """Generate SEO metadata"""
    products_list = products if isinstance(products, list) else [products]
    
    return {
        'title': f"{topic} - Premium Guide | Footbix",
        'slug': topic.lower().replace(' ', '-'),
        'meta_description': f"Expert guide to {topic}. Compare {', '.join(products_list)} with specs, pros/cons, and recommendations.",
        'keywords': [
            topic,
            f"best {topic.lower()}",
            f"{products_list[0]} review",
            f"{topic.lower()} buying guide",
            "soccer equipment"
        ]
    }

# --- Shopify Products ---
def fetch_shopify_products(first=250, after=None):
    """Fetch all products from Shopify store with images and pricing"""
    try:
        store_url = os.getenv('SHOPIFY_STORE_URL')
        access_token = os.getenv('SHOPIFY_ADMIN_API_TOKEN')
        api_version = os.getenv('SHOPIFY_API_VERSION', '2024-01')
        
        headers_shopify = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        url = f"{store_url}/admin/api/{api_version}/graphql.json"
        
        # Build query with cursor for pagination
        after_clause = f'after: "{after}"' if after else ""
        query = f"""
        {{
          products(first: {first} {after_clause}) {{
            pageInfo {{
              hasNextPage
              endCursor
            }}
            edges {{
              node {{
                id
                title
                handle
                featuredImage {{
                  url
                  altText
                }}
                priceRange {{
                  minVariantPrice {{
                    amount
                    currencyCode
                  }}
                  maxVariantPrice {{
                    amount
                    currencyCode
                  }}
                }}
              }}
            }}
          }}
        }}
        """
        
        all_products = []
        has_next_page = True
        next_cursor = None
        
        while has_next_page:
            query_with_cursor = f"""
            {{
              products(first: 250 {f'after: "{next_cursor}"' if next_cursor else ""}) {{
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
                edges {{
                  node {{
                    id
                    title
                    handle
                    featuredImage {{
                      url
                      altText
                    }}
                    priceRange {{
                      minVariantPrice {{
                        amount
                        currencyCode
                      }}
                      maxVariantPrice {{
                        amount
                        currencyCode
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """
            
            response = requests.post(url, json={'query': query_with_cursor}, headers=headers_shopify, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"GraphQL errors: {data['errors']}")
                    break
                    
                if 'data' in data and 'products' in data['data']:
                    products_data = data['data']['products']
                    
                    for edge in products_data['edges']:
                        node = edge['node']
                        featured_image = node.get('featuredImage')
                        price_range = node.get('priceRange', {})
                        min_price = price_range.get('minVariantPrice', {})
                        
                        # Convert price from cents to dollars
                        price_amount = min_price.get('amount', 'N/A')
                        if price_amount and price_amount != 'N/A':
                            try:
                                price_in_dollars = float(price_amount) / 100
                                formatted_price = f"{price_in_dollars:.2f}"
                            except (ValueError, TypeError):
                                formatted_price = 'N/A'
                        else:
                            formatted_price = 'N/A'
                        
                        all_products.append({
                            'id': node['id'],
                            'title': node['title'],
                            'handle': node['handle'],
                            'image': featured_image.get('url') if featured_image else None,
                            'imageAlt': featured_image.get('altText', node['title']) if featured_image else node['title'],
                            'price': formatted_price,
                            'currency': min_price.get('currencyCode', 'USD')
                        })
                    
                    # Check for next page
                    has_next_page = products_data['pageInfo']['hasNextPage']
                    next_cursor = products_data['pageInfo']['endCursor']
            else:
                print(f"Shopify API error: {response.status_code}")
                break
        
        return all_products
    except Exception as e:
        print(f"Error fetching products: {e}")
        return []

# --- Web Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    """API endpoint to fetch products"""
    products = fetch_shopify_products()
    return jsonify({'status': 'success', 'products': products})

@app.route('/api/product-images', methods=['GET'])
def get_product_images():
    """API endpoint to fetch all product images for image browser"""
    try:
        store_url = os.getenv('SHOPIFY_STORE_URL')
        access_token = os.getenv('SHOPIFY_ADMIN_API_TOKEN')
        api_version = os.getenv('SHOPIFY_API_VERSION', '2024-01')
        
        headers_shopify = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
        url = f"{store_url}/admin/api/{api_version}/graphql.json"
        
        all_images = []
        has_next_page = True
        next_cursor = None
        
        while has_next_page:
            query = f"""
            {{
              products(first: 250 {f'after: "{next_cursor}"' if next_cursor else ""}) {{
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
                edges {{
                  node {{
                    id
                    title
                    handle
                    images(first: 10) {{
                      edges {{
                        node {{
                          id
                          url
                          altText
                          width
                          height
                        }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """
            
            response = requests.post(url, json={'query': query}, headers=headers_shopify, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"GraphQL errors: {data['errors']}")
                    break
                
                if 'data' in data and 'products' in data['data']:
                    products_data = data['data']['products']
                    
                    for edge in products_data['edges']:
                        node = edge['node']
                        product_title = node['title']
                        product_handle = node['handle']
                        
                        for img_edge in node.get('images', {}).get('edges', []):
                            img_node = img_edge['node']
                            all_images.append({
                                'id': img_node['id'],
                                'url': img_node['url'],
                                'altText': img_node.get('altText', product_title),
                                'productTitle': product_title,
                                'productHandle': product_handle,
                                'width': img_node.get('width'),
                                'height': img_node.get('height')
                            })
                    
                    has_next_page = products_data['pageInfo']['hasNextPage']
                    next_cursor = products_data['pageInfo']['endCursor']
            else:
                print(f"Shopify API error: {response.status_code}")
                break
        
        return jsonify({'status': 'success', 'images': all_images})
    except Exception as e:
        print(f"Error fetching product images: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    """Main generation endpoint"""
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        products = data.get('products', '').strip()
        
        if not topic:
            return jsonify({'status': 'error', 'message': 'Topic required'}), 400
        
        products_list = [p.strip() for p in products.split(',') if p.strip()] if products else [topic]
        
        # Step 1: Research
        seo_data = research_keywords(topic)
        if seo_data['status'] != 'success':
            return jsonify({'status': 'error', 'message': f'Research failed: {seo_data.get("message")}'}), 500
        
        # Step 2: Generate content
        content_result = generate_blog_content(topic, products_list)
        if content_result['status'] != 'success':
            return jsonify({'status': 'error', 'message': f'Content generation failed: {content_result.get("message")}'}), 500
        
        # Step 3: Generate metadata
        metadata = generate_metadata(topic, products_list)
        
        # Step 4: Create Shopify draft
        draft_result = create_shopify_draft(
            metadata['title'],
            content_result['content'],
            metadata
        )
        
        if draft_result['status'] != 'success':
            return jsonify({'status': 'error', 'message': f'Draft creation failed: {draft_result.get("message")}'}), 500
        
        return jsonify({
            'status': 'success',
            'message': 'Blog generated successfully!',
            'draft': {
                'title': draft_result['title'],
                'url': draft_result['url'],
                'search_volume': seo_data.get('search_volume', 0),
                'keywords': metadata['keywords']
            }
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Unexpected error: {str(e)}'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)))
