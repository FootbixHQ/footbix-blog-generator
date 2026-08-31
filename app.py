from flask import Flask, render_template, request, jsonify
import requests
import os
import json
from image_routes import images_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(images_bp)

# Only need ONE key now
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
COMPOSIO_BASE_URL = "https://api.composio.dev/v1"

headers = {
    'Authorization': f'Bearer {COMPOSIO_API_KEY}',
    'Content-Type': 'application/json'
}

# --- DataForSEO via Composio ---
def research_keywords(keyword):
    """Research keyword using Composio's DataForSEO connection"""
    print(f"Researching: {keyword}")
    
    url = f"{COMPOSIO_BASE_URL}/connectors/execute"
    payload = {
        'connectorId': 'dataforseo',
        'action': 'search_volume',
        'input': {
            'keyword': keyword
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json().get('result', {})
            return {
                'status': 'success',
                'search_volume': result.get('search_volume', 0),
                'competition': result.get('competition', 'N/A'),
                'cpc': result.get('cpc', 0)
            }
        else:
            return {'status': 'error', 'message': f'DataForSEO error: {response.status_code}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

# --- KoalaWriter via Composio ---
def generate_blog_content(topic, products):
    """Generate blog using Composio's KoalaWriter connection"""
    print(f"Generating content for: {topic}")
    
    products_str = ", ".join(products) if isinstance(products, list) else products
    
    prompt = f"""Write a premium soccer equipment buying guide with this structure:

Topic: {topic}
Products to compare: {products_str}

Structure:
1. Introduction (150 words) - Hook
2. What You Need to Know (200 words)
3. Product Comparison (300 words) - Specs, pros/cons, price
4. Detailed Reviews (400 words)
5. How to Choose (200 words)
6. FAQ (200 words)
7. Conclusion (100 words)

Write professionally, SEO-optimized, ~1500 words."""
    
    try:
        exec_url = f"{COMPOSIO_BASE_URL}/connectors/execute"
        payload = {
            'connectorId': 'koalawriter',
            'action': 'write_content',
            'input': {
                'prompt': prompt,
                'length': 'long',
                'tone': 'professional'
            }
        }
        
        response = requests.post(exec_url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json().get('result', {})
            content = result.get('text', '')
            if content:
                return {'status': 'success', 'content': content}
            else:
                return {'status': 'error', 'message': 'No content generated'}
        else:
            return {'status': 'error', 'message': f'KoalaWriter error: {response.status_code}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

# --- Shopify via Composio ---
def create_shopify_draft(title, content, metadata):
    """Create Shopify draft using Composio's Shopify connection"""
    print(f"Creating Shopify draft: {title}")
    
    try:
        exec_url = f"{COMPOSIO_BASE_URL}/connectors/execute"
        
        body_html = f"""
        <h1>{title}</h1>
        <p><strong>Meta Description:</strong> {metadata['meta_description']}</p>
        <p><strong>Keywords:</strong> {', '.join(metadata['keywords'])}</p>
        <hr>
        {content.replace(chr(10), '<br>')}
        """
        
        payload = {
            'connectorId': 'shopify',
            'action': 'create_blog_article',
            'input': {
                'title': title,
                'body_html': body_html,
                'status': 'draft'
            }
        }
        
        response = requests.post(exec_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json().get('result', {})
            return {
                'status': 'success',
                'id': result.get('id'),
                'url': result.get('url', '#'),
                'title': result.get('title', title)
            }
        else:
            return {
                'status': 'error',
                'message': f'Shopify error: {response.status_code}'
            }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

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
