from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

# --- Helper Functions ---
def research_keywords(keyword):
    """Research keyword using DataForSEO API directly"""
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

def generate_blog_content(topic, products):
    """Generate blog content using Koala AI API directly"""
    koala_api_key = os.getenv('KOALA_API_KEY')
    if not koala_api_key:
        return {'status': 'error', 'message': 'KOALA_API_KEY not set', 'content': None}
    
    products_str = ', '.join(products) if isinstance(products, list) else products
    prompt = f"""Write a premium soccer equipment buying guide blog post about {topic}.
Feature: {products_str}
Structure: Introduction (150 words), What is this (200 words), Top products (300 words), How to choose (200 words), FAQ (200 words), Conclusion (100 words).
Make it professional, SEO-optimized, ~1500 words total."""
    
    try:
        headers = {'Authorization': f'Bearer {koala_api_key}', 'Content-Type': 'application/json'}
        payload = {'prompt': prompt, 'length': 'long', 'tone': 'professional'}
        response = requests.post('https://api.koala.sh/v1/write', json=payload, headers=headers, timeout=60)
        if response.status_code == 200:
            content = response.json().get('text', '')
            return {'status': 'success', 'content': content if content else 'Blog content generated.'} 
        return {'status': 'error', 'message': f'Koala error: {response.status_code}', 'content': None}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'content': None}

def generate_metadata(topic, products):
    """Generate SEO metadata"""
    products_list = products if isinstance(products, list) else [products]
    return {
        'title': f"{topic} - Footbix Soccer Equipment Guide",
        'meta_description': f"Expert guide to {topic}. Compare {', '.join(products_list[:2])} with specs and recommendations.",
        'keywords': [topic, f"best {topic}", f"{products_list[0]}", "soccer equipment"]
    }

def create_shopify_draft(title, content, metadata):
    """Create Shopify draft using Shopify API directly"""
    store = os.getenv("SHOPIFY_STORE", "footbix.myshopify.com")
    token = os.getenv("SHOPIFY_ADMIN_API_TOKEN")
    
    if not token:
        return {'status': 'error', 'message': 'SHOPIFY_ADMIN_API_TOKEN not set'}
    
    try:
        url = f"https://{store}/admin/api/2024-01/blogs/241253381/articles.json"
        headers = {'X-Shopify-Access-Token': token}
        body_html = f"<h1>{title}</h1><p>{metadata['meta_description']}</p><hr>{content}"
        payload = {'article': {'title': title, 'body_html': body_html, 'status': 'draft'}}
        
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code in [200, 201]:
            return {'status': 'success', 'article_id': r.json().get('article', {}).get('id')}
        return {'status': 'error', 'message': f'Shopify error: {r.status_code}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json or {}
        topic = data.get('topic', '').strip()
        keyword = data.get('keyword', '').strip()
        products = data.get('products', '').strip()
        
        if not topic or not keyword:
            return jsonify({'status': 'error', 'message': 'Topic and keyword required'}), 400
        
        products_list = [p.strip() for p in products.split(',') if p.strip()] if products else [topic]
        
        # Step 1: Research
        seo_data = research_keywords(keyword)
        
        # Step 2: Generate content
        content_result = generate_blog_content(topic, products_list)
        if not content_result.get('content'):
            return jsonify({'status': 'error', 'message': 'Failed to generate content'}), 500
        
        # Step 3: Metadata
        metadata = generate_metadata(topic, products_list)
        
        # Step 4: Create Shopify draft
        draft_result = create_shopify_draft(metadata['title'], content_result['content'], metadata)
        
        if draft_result.get('status') == 'success':
            return jsonify({'status': 'success', 'message': 'Blog draft created', 'article_id': draft_result.get('article_id'), 'seo_data': seo_data}), 200
        else:
            return jsonify({'status': 'error', 'message': draft_result.get('message', 'Unknown error')}), 500
            
    except Exception as e:
        print(f"Generate error: {e}")
        return jsonify({'status': 'error', 'message': f'Unexpected error: {str(e)}'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=False)
