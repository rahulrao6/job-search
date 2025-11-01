"""
Simple Flask web app for Job Referral Connection Finder
Deploy to Render.com for easy browser-based testing and sharing
"""

from flask import Flask, request, render_template_string
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.orchestrator import ConnectionFinder

app = Flask(__name__)

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
                <h2>Finding Connections...</h2>
                <p>Searching GitHub, LinkedIn, and company pages</p>
                <p style="font-size: 12px; margin-top: 10px;">This may take 10-20 seconds</p>
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
            background: rgba(102, 126, 234, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        .loading-content {
            text-align: center;
            color: white;
        }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
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
            
            {% for person in people[:10] %}
            <div class="person-card">
                <div class="person-name">{{ person.name }}</div>
                <div class="person-title">{{ person.title }}</div>
                {% if person.linkedin_url %}
                <a href="{{ person.linkedin_url }}" target="_blank" class="person-linkedin">
                    View on LinkedIn →
                </a>
                {% endif %}
                <span class="person-source">from {{ person.source }}</span>
            </div>
            {% endfor %}
            
            {% if people|length > 10 %}
            <div style="text-align: center; color: #999; font-size: 14px; margin-top: 10px;">
                ... and {{ people|length - 10 }} more
            </div>
            {% endif %}
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
        # Find connections (with timeout protection)
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Search took too long")
        
        # Set 30 second timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            finder = ConnectionFinder()
            results = finder.find_connections(company=company, title=role)
        finally:
            signal.alarm(0)  # Cancel timeout
        
        # Extract results
        total_found = results.get('total_found', 0)
        by_category = results.get('by_category', {})
        category_counts = results.get('category_counts', {})
        
        # Convert dict results to objects for template
        categories_display = {}
        for category, people_list in by_category.items():
            if people_list:
                # Convert dict to simple object
                class PersonObj:
                    def __init__(self, d):
                        self.name = d.get('name', 'Unknown')
                        self.title = d.get('title', 'Unknown')
                        self.linkedin_url = d.get('linkedin_url')
                        self.source = d.get('source', 'unknown')
                
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
    # Get port from environment (for Render) or use 8000 (5000 blocked by macOS AirPlay)
    port = int(os.environ.get('PORT', 8000))
    # Run with host 0.0.0.0 so it's accessible externally
    app.run(host='0.0.0.0', port=port, debug=True)

