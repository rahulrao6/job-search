"""
Simple Flask web app for Job Referral Connection Finder
Deploy to Fly.io for production use with auto-scaling
"""

from flask import Flask, request, render_template_string, jsonify
from flask_cors import CORS
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.orchestrator import ConnectionFinder
from src.api.routes import api
from src.api.middleware import handle_api_errors
from src.utils.logger import setup_logging

# Setup logging first (before creating app)
setup_logging(
    log_level=os.getenv('LOG_LEVEL', 'INFO'),
    use_json=os.getenv('LOG_FORMAT', 'json').lower() == 'json' or os.getenv('ENVIRONMENT', '').lower() == 'production'
)

app = Flask(__name__)

# Configure request size limits (16MB max)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Request timeout configuration:
# - Gunicorn worker timeout: 120s (configured in Dockerfile CMD)
#   This handles long-running search operations that may take 10-25 seconds
# - HTTP request timeout: 60s (Fly.io default, can be increased if needed)
# - External API timeouts: 30s per source (configured in source clients)
# - Per-request timeout: No explicit Flask timeout (relies on Gunicorn)

# Configure CORS for frontend proxying
frontend_url = os.getenv('FRONTEND_URL')

# Build list of allowed origins (explicit list, no wildcards for security)
allowed_origins = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

# Add FRONTEND_URL if provided (can be comma-separated list)
if frontend_url:
    if frontend_url == '*':
        # Allow all origins (development only)
        allowed_origins = None
    else:
        # Split comma-separated list
        for url in frontend_url.split(','):
            url = url.strip()
            if url and url not in allowed_origins:
                allowed_origins.append(url)

# Configure Flask-CORS
CORS(app, 
     origins=allowed_origins,  # Explicit list only
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
     allow_headers=['Authorization', 'Content-Type', 'X-Requested-With', 'Accept'],
     supports_credentials=True,
     expose_headers=['Content-Type', 'Authorization'])

# Add error handler for request size exceeded
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle 413 Request Entity Too Large"""
    return jsonify({
        'success': False,
        'error': {
            'code': 'REQUEST_TOO_LARGE',
            'message': 'Request payload too large. Maximum size is 16MB.',
            'details': {}
        }
    }), 413

# Register error handlers
handle_api_errors(app)

# Register API routes
app.register_blueprint(api)

# Add request timing middleware for all routes
@app.before_request
def before_request():
    """Track request start time for all requests"""
    from flask import g
    import time as time_module
    g.request_start_time = time_module.time()

@app.after_request
def after_request_timing(response):
    """Track request metrics and log slow requests"""
    from flask import g, request
    import time as time_module
    
    try:
        if hasattr(g, 'request_start_time'):
            duration_ms = (time_module.time() - g.request_start_time) * 1000
            
            # Log slow requests (>5s) as warnings
            if duration_ms > 5000:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Slow request: {request.path} took {duration_ms:.0f}ms")
            
            # Record metrics
            try:
                from src.utils.metrics import get_metrics_tracker
                metrics = get_metrics_tracker()
                status_code = response.status_code if hasattr(response, 'status_code') else 200
                metrics.record_request(
                    endpoint=request.path,
                    status_code=status_code,
                    duration_ms=duration_ms
                )
            except Exception:
                pass  # Don't fail if metrics tracking fails
    except Exception:
        pass  # Don't fail middleware on errors
    
    return response

# HTML template with inline CSS for simplicity
HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Job Referral Connection Finder</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        .example {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            font-size: 13px;
            color: #666;
        }
        .example strong {
            color: #333;
        }
        .footer {
            margin-top: 20px;
            text-align: center;
            color: #999;
            font-size: 12px;
        }
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(102, 126, 234, 0.95);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            -webkit-backdrop-filter: blur(10px);
            backdrop-filter: blur(10px);
        }
        .loading-content {
            text-align: center;
            color: white;
            padding: 20px;
            max-width: 400px;
        }
        .loading-content h2 {
            font-size: 24px;
            margin-bottom: 15px;
            font-weight: 600;
        }
        .loading-content p {
            font-size: 16px;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin: 0 auto 25px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .progress-dots {
            display: inline-block;
            margin-left: 5px;
        }
        .progress-dots span {
            animation: blink 1.4s infinite both;
            font-size: 20px;
        }
        .progress-dots span:nth-child(2) {
            animation-delay: .2s;
        }
        .progress-dots span:nth-child(3) {
            animation-delay: .4s;
        }
        @keyframes blink {
            0%, 60%, 100% { opacity: 0.3; }
            30% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Find Job Referral Connections</h1>
        <p class="subtitle">Find recruiters, managers, and employees at any company - completely FREE!</p>
        
        <form method="POST" action="/search">
            <div class="form-group">
                <label for="company">Company Name</label>
                <input type="text" id="company" name="company" placeholder="e.g., Google, Amazon, Microsoft" required>
            </div>
            
            <div class="form-group">
                <label for="role">Job Title</label>
                <input type="text" id="role" name="role" placeholder="e.g., Software Engineer, Product Manager" required>
            </div>
            
            <button type="submit" onclick="showLoading()">🔍 Find Connections</button>
        </form>
        
        <div id="loading" class="loading-overlay" style="display: none;">
            <div class="loading-content">
                <div class="spinner"></div>
                <h2>Finding Connections<span class="progress-dots"><span>.</span><span>.</span><span>.</span></span></h2>
                <p>🔍 Searching free sources first</p>
                <p>📊 Google CSE • GitHub API • Company Pages</p>
                <p style="font-size: 14px; margin-top: 15px; opacity: 0.8;">⏱️ This typically takes 10-20 seconds</p>
                <p style="font-size: 12px; margin-top: 10px; opacity: 0.7;">💡 Tip: We prioritize free APIs to keep costs at $0</p>
            </div>
        </div>
        
        <script>
        function showLoading() {
            document.getElementById('loading').style.display = 'flex';
        }
        </script>
        
        <div class="example">
            <strong>💡 How it works:</strong><br>
            1. Enter a company name and job role<br>
            2. We search multiple sources (GitHub, LinkedIn, company pages)<br>
            3. Get recruiters, managers, and peers you can connect with<br>
            4. Reach out for referrals and 10x your application success rate!
        </div>
        
        <div class="footer">
            Built with ❤️ for job seekers
        </div>
    </div>
</body>
</html>
"""

RESULTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Results - {{ company }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 900px;
            margin: 0 auto;
        }
        .header {
            margin-bottom: 30px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        .back-btn {
            display: inline-block;
            padding: 8px 16px;
            background: #f0f0f0;
            color: #333;
            text-decoration: none;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 20px;
            transition: background 0.2s;
        }
        .back-btn:hover {
            background: #e0e0e0;
        }
        .summary {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
        }
        .summary-stat {
            display: inline-block;
            margin-right: 20px;
            font-size: 14px;
            color: #666;
        }
        .summary-stat strong {
            color: #333;
            font-size: 18px;
        }
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(102, 126, 234, 0.95);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            -webkit-backdrop-filter: blur(10px);
            backdrop-filter: blur(10px);
        }
        .loading-content {
            text-align: center;
            color: white;
            padding: 20px;
            max-width: 400px;
        }
        .loading-content h2 {
            font-size: 24px;
            margin-bottom: 15px;
            font-weight: 600;
        }
        .loading-content p {
            font-size: 16px;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin: 0 auto 25px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .progress-dots {
            display: inline-block;
            margin-left: 5px;
        }
        .progress-dots span {
            animation: blink 1.4s infinite both;
            font-size: 20px;
        }
        .progress-dots span:nth-child(2) {
            animation-delay: .2s;
        }
        .progress-dots span:nth-child(3) {
            animation-delay: .4s;
        }
        @keyframes blink {
            0%, 60%, 100% { opacity: 0.3; }
            30% { opacity: 1; }
        }
        .category {
            margin-bottom: 30px;
        }
        .category-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
        .category-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }
        .category-count {
            margin-left: 10px;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .person-card {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            transition: all 0.3s;
        }
        .person-card:hover {
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
            transform: translateY(-2px);
        }
        .person-name {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
        }
        .person-title {
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }
        .person-linkedin {
            display: inline-block;
            padding: 6px 12px;
            background: #0077b5;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 12px;
            transition: background 0.2s;
        }
        .person-linkedin:hover {
            background: #005885;
        }
        .person-source {
            display: inline-block;
            margin-left: 8px;
            font-size: 11px;
            color: #999;
        }
        .person-meta {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #f0f0f0;
            font-size: 12px;
            color: #666;
        }
        .meta-item {
            display: inline-block;
            margin-right: 16px;
            margin-bottom: 4px;
        }
        .meta-label {
            font-weight: 600;
            color: #888;
        }
        .confidence-high {
            color: #10b981;
            font-weight: 600;
        }
        .confidence-medium {
            color: #f59e0b;
            font-weight: 600;
        }
        .confidence-low {
            color: #ef4444;
            font-weight: 600;
        }
        .skill-tag {
            display: inline-block;
            padding: 2px 8px;
            background: #e7f3ff;
            border-radius: 4px;
            font-size: 11px;
            margin-right: 4px;
            margin-bottom: 4px;
            color: #0077b5;
        }
        .no-results {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .error {
            background: #fee;
            border: 2px solid #fcc;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            color: #c33;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← New Search</a>
        
        <div class="header">
            <h1>📊 Connections at {{ company }}</h1>
            <p class="subtitle">for {{ role }}</p>
        </div>
        
        {% if error %}
        <div class="error">
            <strong>⚠️ Error:</strong> {{ error }}
        </div>
        {% endif %}
        
        {% if total_found > 0 %}
        <div class="summary">
            <div class="summary-stat">
                <strong>{{ total_found }}</strong> total connections found
            </div>
            {% if category_counts %}
            {% for category, count in category_counts.items() %}
            <div class="summary-stat">
                <strong>{{ count }}</strong> {{ category }}
            </div>
            {% endfor %}
            {% endif %}
        </div>
        
        {% for category_name, people in categories.items() %}
        {% if people %}
        <div class="category">
            <div class="category-header">
                <span class="category-title">
                    {% if category_name == 'recruiter' %}🎯 Recruiters
                    {% elif category_name == 'manager' %}👔 Managers
                    {% elif category_name == 'senior' %}⭐ Senior Engineers
                    {% elif category_name == 'peer' %}👥 Peers
                    {% else %}{{ category_name }}
                    {% endif %}
                </span>
                <span class="category-count">{{ people|length }}</span>
            </div>
            
            {% for person in people %}
            <div class="person-card">
                <div class="person-name">{{ person.name }}</div>
                <div class="person-title">{{ person.title }}</div>
                
                <div style="margin-top: 8px;">
                    {% if person.linkedin_url %}
                    <a href="{{ person.linkedin_url }}" target="_blank" class="person-linkedin">
                        View on LinkedIn →
                    </a>
                    {% endif %}
                    <span class="person-source">
                        from {{ person.source }}
                        {% if person.source == 'google_serp' or person.source == 'serpapi' %}
                        <span style="color: #10b981; font-weight: 600;">★</span>
                        {% elif person.source == 'github' %}
                        <span style="color: #f59e0b;">⚠</span>
                        {% endif %}
                    </span>
                </div>
                
                <div class="person-meta">
                    {% if person.confidence_score %}
                    <div class="meta-item">
                        <span class="meta-label">Confidence:</span>
                        {% if person.confidence_score >= 0.7 %}
                        <span class="confidence-high">{{ "%.0f"|format(person.confidence_score * 100) }}%</span>
                        {% elif person.confidence_score >= 0.4 %}
                        <span class="confidence-medium">{{ "%.0f"|format(person.confidence_score * 100) }}%</span>
                        {% else %}
                        <span class="confidence-low">{{ "%.0f"|format(person.confidence_score * 100) }}%</span>
                        {% endif %}
                    </div>
                    {% endif %}
                    
                    {% if person.department %}
                    <div class="meta-item">
                        <span class="meta-label">Dept:</span> {{ person.department }}
                    </div>
                    {% endif %}
                    
                    {% if person.location %}
                    <div class="meta-item">
                        <span class="meta-label">Location:</span> {{ person.location }}
                    </div>
                    {% endif %}
                    
                    {% if person.experience_years %}
                    <div class="meta-item">
                        <span class="meta-label">Experience:</span> {{ person.experience_years }} years
                    </div>
                    {% endif %}
                    
                    {% if person.skills %}
                    <div style="margin-top: 8px;">
                        <span class="meta-label">Skills:</span>
                        {% for skill in person.skills[:5] %}
                        <span class="skill-tag">{{ skill }}</span>
                        {% endfor %}
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        {% endfor %}
        
        {% else %}
        <div class="no-results">
            <h2>😔 No connections found</h2>
            <p>Try a different company or role</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    """Home page with search form"""
    return render_template_string(HOME_TEMPLATE)

@app.route('/search', methods=['POST'])
def search():
    """Search for connections"""
    company = request.form.get('company', '').strip()
    role = request.form.get('role', '').strip()
    
    if not company or not role:
        return render_template_string(RESULTS_TEMPLATE, 
                                     company=company or "Unknown",
                                     role=role or "Unknown",
                                     error="Please enter both company name and job title",
                                     total_found=0,
                                     categories={})
    
    try:
        # Find connections
        finder = ConnectionFinder()
        results = finder.find_connections(company=company, title=role)
        
        # Extract results
        total_found = results.get('total_found', 0)
        by_category = results.get('by_category', {})
        category_counts = results.get('category_counts', {})
        
        # Convert dict results to objects for template
        categories_display = {}
        for category, people_list in by_category.items():
            if people_list:
                # Convert dict to simple object with ALL available data
                class PersonObj:
                    def __init__(self, d):
                        self.name = d.get('name', 'Unknown')
                        self.title = d.get('title', 'Unknown')
                        self.linkedin_url = d.get('linkedin_url')
                        self.source = d.get('source', 'unknown')
                        self.confidence_score = d.get('confidence_score', 0.5)
                        self.department = d.get('department')
                        self.location = d.get('location')
                        self.experience_years = d.get('experience_years')
                        self.skills = d.get('skills', [])
                        self.email = d.get('email')
                        self.twitter_url = d.get('twitter_url')
                        self.github_url = d.get('github_url')
                
                categories_display[category] = [PersonObj(p) for p in people_list]
        
        return render_template_string(RESULTS_TEMPLATE,
                                     company=company,
                                     role=role,
                                     total_found=total_found,
                                     categories=categories_display,
                                     category_counts=category_counts,
                                     error=None)
    
    except Exception as e:
        return render_template_string(RESULTS_TEMPLATE,
                                     company=company,
                                     role=role,
                                     error=str(e),
                                     total_found=0,
                                     categories={})

if __name__ == '__main__':
    # Get port from environment or use 8080 (default for Fly.io)
    port = int(os.environ.get('PORT', 8080))
    # Run with host 0.0.0.0 so it's accessible externally
    # Debug mode disabled for production (signal issues in worker threads)
    app.run(host='0.0.0.0', port=port, debug=False)

