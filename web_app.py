"""
Simple Flask web app for Job Referral Connection Finder
Deploy to Render.com for easy browser-based testing and sharing
"""

from flask import Flask, request, render_template_string
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

app = Flask(__name__)

# Configure CORS
# Allow localhost for development, Vercel domains, and FRONTEND_URL env var
frontend_url = os.getenv('FRONTEND_URL')

# Build list of allowed origins
allowed_origins = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://frontend-job-drab.vercel.app',  # Your specific Vercel frontend
]

# Add FRONTEND_URL if provided
if frontend_url and frontend_url != '*':
    if frontend_url not in allowed_origins:
        allowed_origins.append(frontend_url)

# Handle CORS manually for Vercel domains since Flask-CORS doesn't support wildcards
# We'll add an after_request handler to allow any .vercel.app domain
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin', '')
    
    # Allow Vercel domains
    if origin and '.vercel.app' in origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
        response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, X-Requested-With, Accept'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Type, Authorization'
    
    return response

# Configure Flask-CORS for explicit origins
CORS(app, 
     origins=allowed_origins if frontend_url != '*' else None,  # None = allow all if FRONTEND_URL=*
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
     allow_headers=['Authorization', 'Content-Type', 'X-Requested-With', 'Accept'],
     supports_credentials=True,
     expose_headers=['Content-Type', 'Authorization'])

# Register error handlers
handle_api_errors(app)

# Register API routes
app.register_blueprint(api)

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
        
        <div class="example" style="background: #e7f3ff; border-left: 4px solid #0077b5; margin-top: 15px;">
            <strong>🧪 For Developers:</strong><br>
            <a href="/api-test" style="color: #0077b5; font-weight: 600;">Test API Endpoints →</a><br>
            Interactive UI to test all REST API endpoints with authentication
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
        # Find connections (Render has its own timeout protection)
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


# API Testing UI Template
API_TEST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>API Testing Interface</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        .nav-links {
            margin-top: 15px;
        }
        .nav-links a {
            color: #667eea;
            text-decoration: none;
            margin-right: 20px;
            font-size: 14px;
        }
        .nav-links a:hover {
            text-decoration: underline;
        }
        .endpoint-section {
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .endpoint-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        .endpoint-method {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 10px;
        }
        .method-get { background: #10b981; color: white; }
        .method-post { background: #3b82f6; color: white; }
        .endpoint-path {
            color: #666;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .form-group {
            margin: 15px 0;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
        }
        textarea {
            font-family: 'Courier New', monospace;
            min-height: 100px;
            resize: vertical;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .response-box {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }
        .response-box pre {
            margin: 0;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #333;
        }
        .error-box {
            border-left-color: #ef4444;
            background: #fee;
        }
        .success-box {
            border-left-color: #10b981;
            background: #f0fdf4;
        }
        .loading {
            display: inline-block;
            margin-left: 10px;
            color: #667eea;
        }
        .help-text {
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }
        .token-status {
            padding: 10px;
            background: #fff3cd;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .token-valid {
            background: #d1f4e0;
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        @media (max-width: 768px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 API Testing Interface</h1>
            <p class="subtitle">Test all API endpoints with a visual interface</p>
            <div class="nav-links">
                <a href="/">← Back to Simple Search</a>
                <a href="#health">Health</a>
                <a href="#auth">Auth Setup</a>
                <a href="#profile">Profile</a>
                <a href="#search">Search</a>
                <a href="#resume">Resume</a>
            </div>
        </div>

        <!-- Token Setup -->
        <div class="endpoint-section" id="auth">
            <div class="endpoint-title">🔐 Authentication Setup</div>
            <p style="color: #666; font-size: 14px; margin: 10px 0;">Most endpoints require a JWT token. Get yours from Supabase Auth after logging in.</p>
            <div class="form-group">
                <label for="jwt-token">JWT Token</label>
                <input type="text" id="jwt-token" placeholder="Paste your Supabase JWT token here">
                <div class="help-text">Store your token here - it will be used for all authenticated requests</div>
            </div>
            <button onclick="saveToken()">💾 Save Token</button>
        </div>

        <!-- Health Check -->
        <div class="endpoint-section" id="health">
            <div class="endpoint-title">
                <span class="endpoint-method method-get">GET</span>
                <span class="endpoint-path">/api/v1/health</span>
            </div>
            <p style="color: #666; font-size: 14px; margin: 10px 0;">Check API and database health (no auth required)</p>
            <button onclick="testHealth()">🏥 Check Health</button>
            <div id="health-response"></div>
        </div>

        <!-- Get Quota -->
        <div class="endpoint-section">
            <div class="endpoint-title">
                <span class="endpoint-method method-get">GET</span>
                <span class="endpoint-path">/api/v1/quota</span>
            </div>
            <p style="color: #666; font-size: 14px; margin: 10px 0;">Get your remaining search quota (requires auth)</p>
            <button onclick="testQuota()">📊 Get Quota</button>
            <div id="quota-response"></div>
        </div>

        <!-- Get Profile -->
        <div class="endpoint-section" id="profile">
            <div class="endpoint-title">
                <span class="endpoint-method method-get">GET</span>
                <span class="endpoint-path">/api/v1/profile</span>
            </div>
            <p style="color: #666; font-size: 14px; margin: 10px 0;">Get your saved profile data</p>
            <button onclick="testGetProfile()">👤 Get Profile</button>
            <div id="get-profile-response"></div>
        </div>

        <!-- Save Profile -->
        <div class="endpoint-section">
            <div class="endpoint-title">
                <span class="endpoint-method method-post">POST</span>
                <span class="endpoint-path">/api/v1/profile/save</span>
            </div>
            <p style="color: #666; font-size: 14px; margin: 10px 0;">Save your profile information</p>
            <div class="grid-2">
                <div class="form-group">
                    <label>Full Name</label>
                    <input type="text" id="profile-name" placeholder="John Doe">
                </div>
                <div class="form-group">
                    <label>Current Title</label>
                    <input type="text" id="profile-title" placeholder="Senior Software Engineer">
                </div>
            </div>
            <div class="form-group">
                <label>Skills (comma-separated)</label>
                <input type="text" id="profile-skills" placeholder="Python, Go, Kubernetes">
            </div>
            <div class="form-group">
                <label>Past Companies (comma-separated)</label>
                <input type="text" id="profile-companies" placeholder="Google, Meta">
            </div>
            <div class="form-group">
                <label>Schools (comma-separated)</label>
                <input type="text" id="profile-schools" placeholder="Stanford, MIT">
            </div>
            <button onclick="testSaveProfile()">💾 Save Profile</button>
            <div id="save-profile-response"></div>
        </div>

        <!-- Search -->
        <div class="endpoint-section" id="search">
            <div class="endpoint-title">
                <span class="endpoint-method method-post">POST</span>
                <span class="endpoint-path">/api/v1/search</span>
            </div>
            <p style="color: #666; font-size: 14px; margin: 10px 0;">Search for connections at a company</p>
            <div class="grid-2">
                <div class="form-group">
                    <label>Company Name *</label>
                    <input type="text" id="search-company" placeholder="Stripe" value="Stripe">
                </div>
                <div class="form-group">
                    <label>Job Title *</label>
                    <input type="text" id="search-title" placeholder="Software Engineer" value="Software Engineer">
                </div>
            </div>
            <div class="form-group">
                <label>Advanced Options (JSON)</label>
                <textarea id="search-advanced" placeholder='{"profile": {"skills": ["Python", "Go"]}, "filters": {"categories": ["recruiter", "manager"]}}'></textarea>
                <div class="help-text">Optional: Add profile data, filters, job_url, etc. as JSON</div>
            </div>
            <button onclick="testSearch()">🔍 Search Connections</button>
            <div id="search-response"></div>
        </div>

        <!-- Parse Job URL -->
        <div class="endpoint-section">
            <div class="endpoint-title">
                <span class="endpoint-method method-post">POST</span>
                <span class="endpoint-path">/api/v1/job/parse</span>
            </div>
            <p style="color: #666; font-size: 14px; margin: 10px 0;">Parse job details from a URL</p>
            <div class="form-group">
                <label>Job URL</label>
                <input type="text" id="job-url" placeholder="https://careers.google.com/jobs/12345">
            </div>
            <button onclick="testParseJob()">🔗 Parse Job</button>
            <div id="parse-job-response"></div>
        </div>

        <!-- Resume Upload -->
        <div class="endpoint-section" id="resume">
            <div class="endpoint-title">
                <span class="endpoint-method method-post">POST</span>
                <span class="endpoint-path">/api/v1/resume/upload</span>
            </div>
            <p style="color: #666; font-size: 14px; margin: 10px 0;">Upload and parse your resume (PDF only)</p>
            <div class="form-group">
                <label>Resume PDF</label>
                <input type="file" id="resume-file" accept=".pdf">
            </div>
            <button onclick="testResumeUpload()">📄 Upload Resume</button>
            <div id="resume-response"></div>
        </div>
    </div>

    <script>
        const BASE_URL = window.location.origin;
        let authToken = localStorage.getItem('api_test_token') || '';
        
        // Load saved token on page load
        window.addEventListener('DOMContentLoaded', function() {
            if (authToken) {
                document.getElementById('jwt-token').value = authToken;
            }
        });

        function saveToken() {
            authToken = document.getElementById('jwt-token').value.trim();
            localStorage.setItem('api_test_token', authToken);
            alert('Token saved! It will be used for authenticated requests.');
        }

        function showResponse(elementId, data, isError = false) {
            const element = document.getElementById(elementId);
            const responseClass = isError ? 'response-box error-box' : 'response-box success-box';
            element.innerHTML = `<div class="${responseClass}"><pre>${JSON.stringify(data, null, 2)}</pre></div>`;
        }

        function showLoading(elementId) {
            const element = document.getElementById(elementId);
            element.innerHTML = '<div class="loading">⏳ Loading...</div>';
        }

        async function testHealth() {
            showLoading('health-response');
            try {
                const response = await fetch(`${BASE_URL}/api/v1/health`);
                const data = await response.json();
                showResponse('health-response', data, !response.ok);
            } catch (error) {
                showResponse('health-response', { error: error.message }, true);
            }
        }

        async function testQuota() {
            if (!authToken) {
                alert('Please set your JWT token first!');
                return;
            }
            showLoading('quota-response');
            try {
                const response = await fetch(`${BASE_URL}/api/v1/quota`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const data = await response.json();
                showResponse('quota-response', data, !response.ok);
            } catch (error) {
                showResponse('quota-response', { error: error.message }, true);
            }
        }

        async function testGetProfile() {
            if (!authToken) {
                alert('Please set your JWT token first!');
                return;
            }
            showLoading('get-profile-response');
            try {
                const response = await fetch(`${BASE_URL}/api/v1/profile`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const data = await response.json();
                showResponse('get-profile-response', data, !response.ok);
            } catch (error) {
                showResponse('get-profile-response', { error: error.message }, true);
            }
        }

        async function testSaveProfile() {
            if (!authToken) {
                alert('Please set your JWT token first!');
                return;
            }
            showLoading('save-profile-response');
            
            const skills = document.getElementById('profile-skills').value.split(',').map(s => s.trim()).filter(s => s);
            const companies = document.getElementById('profile-companies').value.split(',').map(s => s.trim()).filter(s => s);
            const schools = document.getElementById('profile-schools').value.split(',').map(s => s.trim()).filter(s => s);
            
            const profileData = {
                profile: {
                    full_name: document.getElementById('profile-name').value,
                    current_title: document.getElementById('profile-title').value,
                    skills: skills,
                    past_companies: companies,
                    schools: schools
                }
            };
            
            try {
                const response = await fetch(`${BASE_URL}/api/v1/profile/save`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${authToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(profileData)
                });
                const data = await response.json();
                showResponse('save-profile-response', data, !response.ok);
            } catch (error) {
                showResponse('save-profile-response', { error: error.message }, true);
            }
        }

        async function testSearch() {
            if (!authToken) {
                alert('Please set your JWT token first!');
                return;
            }
            showLoading('search-response');
            
            const company = document.getElementById('search-company').value;
            const jobTitle = document.getElementById('search-title').value;
            const advancedJson = document.getElementById('search-advanced').value;
            
            if (!company || !jobTitle) {
                alert('Company and Job Title are required!');
                return;
            }
            
            let searchData = {
                company: company,
                job_title: jobTitle
            };
            
            // Merge advanced options if provided
            if (advancedJson.trim()) {
                try {
                    const advanced = JSON.parse(advancedJson);
                    searchData = { ...searchData, ...advanced };
                } catch (e) {
                    alert('Invalid JSON in Advanced Options: ' + e.message);
                    return;
                }
            }
            
            try {
                const response = await fetch(`${BASE_URL}/api/v1/search`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${authToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(searchData)
                });
                const data = await response.json();
                
                // Display enhanced results if search was successful
                if (data.success && data.data && data.data.results) {
                    displaySearchResults(data, company, jobTitle);
                } else {
                    showResponse('search-response', data, !response.ok);
                }
            } catch (error) {
                showResponse('search-response', { error: error.message }, true);
            }
        }

        function displaySearchResults(data, company, jobTitle) {
            const element = document.getElementById('search-response');
            const results = data.data.results;
            const insights = data.data.insights;
            const quota = data.data.quota;
            
            const totalFound = results.total_found || 0;
            const byCategory = results.by_category || {};
            const categoryCounts = results.category_counts || {};
            
            let html = '<div style="margin-top: 20px;">';
            
            // Header
            html += `
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 20px;">
                    <h2 style="margin: 0 0 10px 0; font-size: 24px;">🎯 Search Results</h2>
                    <div style="font-size: 16px; opacity: 0.9;">${company} • ${jobTitle}</div>
                    <div style="margin-top: 15px; font-size: 20px; font-weight: 600;">Found ${totalFound} connections</div>
                </div>
            `;
            
            // Category Summary
            if (Object.keys(categoryCounts).length > 0) {
                html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 25px;">';
                for (const [category, count] of Object.entries(categoryCounts)) {
                    const emoji = category === 'recruiter' ? '🎯' : category === 'manager' ? '👔' : category === 'senior' ? '⭐' : category === 'peer' ? '👥' : category === 'unknown' ? '❓' : '👤';
                    const color = category === 'recruiter' ? '#dc2626' : category === 'manager' ? '#2563eb' : category === 'senior' ? '#7c3aed' : category === 'peer' ? '#059669' : '#6b7280';
                    html += `
                        <div style="background: white; border-left: 4px solid ${color}; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="font-size: 28px; font-weight: 700; color: ${color};">${count}</div>
                            <div style="font-size: 14px; color: #6b7280; margin-top: 5px;">${emoji} ${category.charAt(0).toUpperCase() + category.slice(1)}s</div>
                        </div>
                    `;
                }
                html += '</div>';
            }
            
            // Insights
            if (insights && (insights.common_backgrounds?.length > 0 || insights.skill_matches?.length > 0 || insights.school_connections?.length > 0)) {
                html += '<div style="background: #eff6ff; padding: 20px; border-radius: 10px; margin-bottom: 25px; border-left: 4px solid #3b82f6;">';
                html += '<h3 style="margin: 0 0 15px 0; color: #1e40af; font-size: 18px;">💡 Match Insights</h3>';
                if (insights.common_backgrounds && insights.common_backgrounds.length > 0) {
                    html += `<div style="margin-bottom: 10px;"><strong style="color: #1e3a8a;">Common backgrounds:</strong> ${insights.common_backgrounds.join(', ')}</div>`;
                }
                if (insights.skill_matches && insights.skill_matches.length > 0) {
                    html += `<div style="margin-bottom: 10px;"><strong style="color: #1e3a8a;">Your matching skills:</strong> ${insights.skill_matches.join(', ')}</div>`;
                }
                if (insights.school_connections && insights.school_connections.length > 0) {
                    html += `<div><strong style="color: #1e3a8a;">School connections:</strong> ${insights.school_connections.join(', ')}</div>`;
                }
                html += '</div>';
            }
            
            // Quota info
            if (quota) {
                const remaining = quota.searches_remaining || 0;
                const total = quota.searches_per_month || 10;
                const percentage = (remaining / total) * 100;
                const barColor = percentage > 50 ? '#10b981' : percentage > 20 ? '#f59e0b' : '#ef4444';
                html += `
                    <div style="background: #f9fafb; padding: 15px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #e5e7eb;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <strong style="color: #374151; font-size: 14px;">Search Quota</strong>
                            <span style="color: ${barColor}; font-weight: 600;">${remaining}/${total} remaining</span>
                        </div>
                        <div style="background: #e5e7eb; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div style="background: ${barColor}; height: 100%; width: ${percentage}%; transition: width 0.3s;"></div>
                        </div>
                    </div>
                `;
            }
            
            // Connections by category
            const categoryOrder = ['recruiter', 'manager', 'senior', 'peer', 'unknown'];
            for (const category of categoryOrder) {
                const people = byCategory[category];
                if (!people || people.length === 0) continue;
                
                const categoryEmoji = category === 'recruiter' ? '🎯' : category === 'manager' ? '👔' : category === 'senior' ? '⭐' : category === 'peer' ? '👥' : '❓';
                const categoryColor = category === 'recruiter' ? '#dc2626' : category === 'manager' ? '#2563eb' : category === 'senior' ? '#7c3aed' : category === 'peer' ? '#059669' : '#6b7280';
                
                html += `
                    <div style="margin-bottom: 35px;">
                        <h3 style="color: ${categoryColor}; border-bottom: 3px solid ${categoryColor}; padding-bottom: 12px; margin-bottom: 20px; font-size: 20px;">
                            ${categoryEmoji} ${category.charAt(0).toUpperCase() + category.slice(1)}s <span style="color: #6b7280; font-size: 16px; font-weight: normal;">(${people.length})</span>
                        </h3>
                `;
                
                people.forEach((person, index) => {
                    const confidence = Math.round((person.confidence || 0.5) * 100);
                    const relevance = person.relevance_score ? Math.round(person.relevance_score * 100) : null;
                    const confidenceColor = confidence >= 70 ? '#10b981' : confidence >= 50 ? '#f59e0b' : '#ef4444';
                    
                    html += `
                        <div style="background: white; border: 2px solid #e5e7eb; border-radius: 12px; padding: 24px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); transition: all 0.3s; position: relative;" 
                             onmouseover="this.style.boxShadow='0 8px 16px rgba(0,0,0,0.1)'; this.style.borderColor='${categoryColor}';"
                             onmouseout="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.05)'; this.style.borderColor='#e5e7eb';">
                            
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                                <div style="flex: 1;">
                                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                                        <h4 style="margin: 0; color: #111827; font-size: 20px; font-weight: 600;">${person.name || 'Unknown'}</h4>
                                        <span style="background: ${categoryColor}20; color: ${categoryColor}; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;">${category}</span>
                                    </div>
                                    <div style="color: #4b5563; font-size: 15px; margin-bottom: 4px; font-weight: 500;">${person.title || 'N/A'}</div>
                                    ${person.company ? `<div style="color: #6b7280; font-size: 14px;">@ ${person.company}</div>` : ''}
                                </div>
                                <div style="text-align: right;">
                                    <div style="background: ${confidenceColor}; color: white; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; margin-bottom: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                        ${confidence}% Match
                                    </div>
                                    ${relevance ? `<div style="color: #6b7280; font-size: 12px; font-weight: 600;">Relevance: ${relevance}%</div>` : ''}
                                </div>
                            </div>
                            
                            ${person.linkedin_url ? `
                                <div style="margin: 15px 0;">
                                    <a href="${person.linkedin_url}" target="_blank" rel="noopener noreferrer" 
                                       style="display: inline-flex; align-items: center; gap: 8px; background: #0077b5; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600; transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,119,181,0.3);"
                                       onmouseover="this.style.background='#005885'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0,119,181,0.4)';"
                                       onmouseout="this.style.background='#0077b5'; this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,119,181,0.3)';">
                                        <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
                                        View LinkedIn Profile
                                    </a>
                                    ${person.email ? `<a href="mailto:${person.email}" style="display: inline-flex; align-items: center; gap: 6px; margin-left: 10px; color: #6b7280; text-decoration: none; font-size: 13px;" onmouseover="this.style.color='#111827';" onmouseout="this.style.color='#6b7280';">📧 ${person.email}</a>` : ''}
                                </div>
                            ` : ''}
                            
                            <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 15px; padding-top: 15px; border-top: 1px solid #e5e7eb; font-size: 13px; color: #6b7280;">
                                ${person.department ? `<div><strong style="color: #374151;">Department:</strong> ${person.department}</div>` : ''}
                                ${person.location ? `<div><strong style="color: #374151;">Location:</strong> ${person.location}</div>` : ''}
                                ${person.source ? `<div><strong style="color: #374151;">Source:</strong> <span style="background: #f3f4f6; padding: 2px 8px; border-radius: 4px; font-size: 11px;">${person.source}</span></div>` : ''}
                            </div>
                            
                            ${person.match_reasons && person.match_reasons.length > 0 ? `
                                <div style="margin-top: 15px; padding: 15px; background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border-radius: 8px; border-left: 3px solid #10b981;">
                                    <div style="font-weight: 600; font-size: 13px; color: #065f46; margin-bottom: 8px;">✨ Why this is a great match:</div>
                                    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #047857; line-height: 1.6;">
                                        ${person.match_reasons.map(reason => `<li style="margin-bottom: 4px;">${reason}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                            
                            ${person.skills && person.skills.length > 0 ? `
                                <div style="margin-top: 15px;">
                                    <div style="font-weight: 600; font-size: 13px; color: #374151; margin-bottom: 8px;">🛠️ Skills:</div>
                                    <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                                        ${person.skills.slice(0, 10).map(skill => 
                                            `<span style="background: #dbeafe; color: #1e40af; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500;">${skill}</span>`
                                        ).join('')}
                                        ${person.skills.length > 10 ? `<span style="color: #6b7280; font-size: 11px; padding: 4px;">+${person.skills.length - 10} more</span>` : ''}
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    `;
                });
                
                html += '</div>';
            }
            
            // No results message
            if (totalFound === 0) {
                html += `
                    <div style="text-align: center; padding: 60px 20px; background: #f9fafb; border-radius: 12px; border: 2px dashed #d1d5db;">
                        <div style="font-size: 48px; margin-bottom: 20px;">😔</div>
                        <h3 style="color: #374151; margin: 0 0 10px 0;">No connections found</h3>
                        <p style="color: #6b7280; margin: 0;">Try adjusting your search criteria or filters</p>
                    </div>
                `;
            }
            
            html += '</div>';
            element.innerHTML = html;
        }

        async function testParseJob() {
            if (!authToken) {
                alert('Please set your JWT token first!');
                return;
            }
            showLoading('parse-job-response');
            
            const jobUrl = document.getElementById('job-url').value;
            if (!jobUrl) {
                alert('Job URL is required!');
                return;
            }
            
            try {
                const response = await fetch(`${BASE_URL}/api/v1/job/parse`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${authToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ job_url: jobUrl })
                });
                const data = await response.json();
                showResponse('parse-job-response', data, !response.ok);
            } catch (error) {
                showResponse('parse-job-response', { error: error.message }, true);
            }
        }

        async function testResumeUpload() {
            if (!authToken) {
                alert('Please set your JWT token first!');
                return;
            }
            showLoading('resume-response');
            
            const fileInput = document.getElementById('resume-file');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a PDF file!');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch(`${BASE_URL}/api/v1/resume/upload`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: formData
                });
                const data = await response.json();
                showResponse('resume-response', data, !response.ok);
            } catch (error) {
                showResponse('resume-response', { error: error.message }, true);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/api-test')
def api_test():
    """API Testing UI"""
    return render_template_string(API_TEST_TEMPLATE)

if __name__ == '__main__':
    # Get port from environment (for Render) or use 8000 (5000 blocked by macOS AirPlay)
    port = int(os.environ.get('PORT', 8000))
    # Run with host 0.0.0.0 so it's accessible externally
    # Debug mode disabled for production (signal issues in worker threads)
    app.run(host='0.0.0.0', port=port, debug=False)

