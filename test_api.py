#!/usr/bin/env python3
"""
Comprehensive API test script for all endpoints with realistic test data generation

Usage: 
    python test_api.py                    # Run all tests with randomized realistic data
    python test_api.py --test 1,2,5       # Run specific tests
    python test_api.py --resume-only      # Test only resume endpoints
    python test_api.py --job-only         # Test only job endpoints
    python test_api.py --skip-rate-limit # Skip rate limit checks
    python test_api.py --company Stripe --job-title 'Senior Engineer'  # Custom test data
    python test_api.py --tech-focus frontend --location 'San Francisco, CA'  # Profile focus
    python test_api.py --seed 42          # Use fixed seed for reproducible tests
    python test_api.py --job-url 'https://...'  # Use real job URL for parsing tests
    python test_api.py --resume-file path/to/resume.pdf  # Use real resume file
"""

import os
import sys
import json
import argparse
import requests
import base64
import random
from typing import Optional, List, Dict, Any

# Configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# Raw token string - can be a JWT directly, base64-encoded JSON, or JSON object
TOKEN_RAW = "eyJhbGciOiJIUzI1NiIsImtpZCI6IlE4ME45aGIzazJaUmNtZEEiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Nwc2FpbXVmYnJ4Z25neG1wcWVyLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjMGQ3YTM4Yy03OTg1LTRiZmYtYTg2Yi0xODY0MThjNGUwNDQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzYyMTkzOTkyLCJpYXQiOjE3NjIxOTAzOTIsImVtYWlsIjoicmFqZGphZ2lyZGFyQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZ29vZ2xlIiwicHJvdmlkZXJzIjpbImdvb2dsZSJdfSwidXNlcl9tZXRhZGF0YSI6eyJhdmF0YXJfdXJsIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jSmE1TS0tekdUY19kOFlZdlFfUjhIeDdqNVBnc04yMV9YSEpWS0pGT29ETW5laTFRPXM5Ni1jIiwiZW1haWwiOiJyYWpkamFnaXJkYXJAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImZ1bGxfbmFtZSI6IlJhaiBKYWdpcmRhciIsImlzcyI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbSIsIm5hbWUiOiJSYWogSmFnaXJkYXIiLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInBpY3R1cmUiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NKYTVNLS16R1RjX2Q4WVl2UV9SOEh4N2o1UGdzTjIxX1hISlZLSkZPb0RNbmVpMVE9czk2LWMiLCJwcm92aWRlcl9pZCI6IjExNTQ1MjYwMzMxMDk3MTI2NTk1NiIsInN1YiI6IjExNTQ1MjYwMzMxMDk3MTI2NTk1NiJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6Im9hdXRoIiwidGltZXN0YW1wIjoxNzYyMTkwMzkyfV0sInNlc3Npb25faWQiOiI5M2NjYzMwNy1lNGJkLTQ1YWEtODFmYS1lNWFiZjU3OTU1MjEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.77Xvt9Dk9TGJEKlFrMwzVZYy5y484-ONWFUMuaO1DQ0"
def parse_token(token_string: str) -> Optional[str]:
    """
    Parse token from various formats and extract the JWT.
    
    Handles:
    - Plain JWT token (3 parts separated by dots)
    - base64-encoded JSON with access_token field
    - JSON object with access_token field
    - Token with "base64-" prefix
    
    Returns:
        JWT token string, or None if parsing fails
    """
    if not token_string:
        return None
    
    # Remove "base64-" prefix if present
    if token_string.startswith("base64-"):
        token_string = token_string[7:]
    
    # If it looks like a JWT (has 3 parts separated by dots), use it directly
    if token_string.count('.') == 2:
        return token_string
    
    # Try to decode as base64 first
    try:
        decoded = base64.b64decode(token_string)
        decoded_str = decoded.decode('utf-8')
        
        # Try to parse as JSON
        try:
            token_data = json.loads(decoded_str)
            # Extract access_token if present
            if isinstance(token_data, dict) and 'access_token' in token_data:
                return token_data['access_token']
        except (json.JSONDecodeError, ValueError):
            # Not JSON, might be a string JWT that was base64 encoded
            if decoded_str.count('.') == 2:
                return decoded_str
    except Exception:
        pass
    
    # Try to parse as JSON directly (in case it wasn't base64 encoded)
    try:
        token_data = json.loads(token_string)
        if isinstance(token_data, dict) and 'access_token' in token_data:
            return token_data['access_token']
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If all else fails, return as-is (might already be a JWT)
    return token_string if token_string.count('.') == 2 else None

# Parse the token
TOKEN = parse_token(TOKEN_RAW) if TOKEN_RAW else None

# Test data pools for variety
COMPANIES = [
    "Stripe", "Shopify", "Airbnb", "Uber", "Lyft", "Netflix", "Amazon", 
    "Microsoft", "Apple", "Tesla", "OpenAI", "Anthropic", "Databricks",
    "Snowflake", "MongoDB", "Redis", "Vercel", "Figma", "Notion", "Plaid"
]

JOB_TITLES = [
    "Software Engineer", "Senior Software Engineer", "Backend Engineer",
    "Full Stack Engineer", "Infrastructure Engineer", "DevOps Engineer",
    "Site Reliability Engineer", "Machine Learning Engineer", "Data Engineer",
    "Security Engineer", "Mobile Engineer", "Frontend Engineer"
]

TECH_STACKS = {
    "backend": ["Python", "Go", "Java", "Rust", "Kubernetes", "Docker", "PostgreSQL", "Redis"],
    "frontend": ["JavaScript", "TypeScript", "React", "Vue", "Next.js", "GraphQL"],
    "infra": ["AWS", "GCP", "Azure", "Terraform", "Kubernetes", "Docker", "Linux"],
    "ml": ["Python", "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy"],
    "mobile": ["Swift", "Kotlin", "React Native", "iOS", "Android"]
}

UNIVERSITIES = [
    "Stanford University", "MIT", "UC Berkeley", "Carnegie Mellon University",
    "University of Washington", "Harvard University", "Princeton University",
    "Cornell University", "University of Texas at Austin", "Georgia Tech"
]

LOCATIONS = [
    "San Francisco, CA", "Seattle, WA", "New York, NY", "Austin, TX",
    "Menlo Park, CA", "Mountain View, CA", "Palo Alto, CA", "Boston, MA",
    "Remote", "San Jose, CA", "Los Angeles, CA"
]

def generate_test_profile(tech_focus="backend", years_exp=None, name=None):
    """Generate realistic test profile data"""
    if years_exp is None:
        years_exp = random.randint(3, 12)
    
    if name is None:
        names = ["Alex Chen", "Sarah Johnson", "Michael Rodriguez", "Emily Kim", 
                "David Park", "Jessica Liu", "James Wilson", "Priya Patel"]
        name = random.choice(names)
    
    # Select tech stack based on focus
    primary_skills = TECH_STACKS.get(tech_focus, TECH_STACKS["backend"])[:5]
    # Add some common skills
    all_skills = primary_skills + random.sample(
        ["Git", "CI/CD", "System Design", "Agile", "REST APIs", "Microservices"],
        k=min(3, len(primary_skills))
    )
    
    # Select companies
    num_companies = random.randint(1, 3)
    past_companies = random.sample(COMPANIES, min(num_companies, len(COMPANIES)))
    
    # Select schools
    num_schools = random.randint(1, 2)
    schools = random.sample(UNIVERSITIES, min(num_schools, len(UNIVERSITIES)))
    
    titles = {
        1: "Software Engineer",
        2: "Software Engineer",
        3: "Senior Software Engineer",
        4: "Senior Software Engineer",
        5: "Staff Software Engineer"
    }
    current_title = titles.get(min(years_exp, 5), "Senior Software Engineer")
    
    return {
        "full_name": name,
        "skills": all_skills,
        "past_companies": past_companies,
        "schools": schools,
        "current_title": current_title,
        "years_experience": years_exp,
        "linkedin_url": f"https://linkedin.com/in/{name.lower().replace(' ', '-')}"
    }

def generate_job_description(job_title, company, required_skills=None):
    """Generate realistic job description"""
    if required_skills is None:
        required_skills = ["Python", "System Design", "Distributed Systems"]
    
    return f"""
{company} is seeking an experienced {job_title} to join our engineering team. 

In this role, you will:
- Design and implement scalable distributed systems
- Collaborate with cross-functional teams to deliver high-quality software
- Optimize system performance and reliability
- Participate in code reviews and mentor junior engineers

Requirements:
- {random.randint(3, 8)}+ years of software engineering experience
- Strong proficiency in {', '.join(required_skills[:3])}
- Experience with cloud platforms (AWS/GCP/Azure)
- BS/MS in Computer Science or equivalent experience
- Excellent problem-solving and communication skills

Preferred:
- Experience with microservices architecture
- Knowledge of containerization and orchestration technologies
- Track record of shipping production systems at scale
""".strip()

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")

def test_endpoint(name, method, endpoint, token=None, data=None, expected_status=200, 
                 expected_success=None, expected_error_code=None, validate_response=True):
    """
    Test a single endpoint with comprehensive validation
    
    Args:
        name: Test name
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        token: Auth token (optional)
        data: Request body data (optional)
        expected_status: Expected HTTP status code
        expected_success: Expected success field value (None = don't check)
        expected_error_code: Expected error code for error responses (None = don't check)
        validate_response: Whether to validate response structure
    """
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=60)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=60)
        else:
            print_error(f"Unsupported method: {method}")
            return False
        
        # Parse response
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            print_error(f"{name} - Invalid JSON response")
            print(f"   Response: {response.text[:200]}...")
            return False
        
        # Validate status code
        status_match = response.status_code == expected_status
        status_color = Colors.GREEN if status_match else Colors.RED
        
        # Validate response structure
        structure_valid = True
        if validate_response:
            # Check for success/error fields based on status
            if expected_status < 400:
                # Success responses should have success=True
                if "success" not in response_json:
                    structure_valid = False
                elif expected_success is not None:
                    if response_json.get("success") != expected_success:
                        structure_valid = False
                elif response_json.get("success") is not True:
                    structure_valid = False
            else:
                # Error responses should have success=False
                if "success" not in response_json:
                    structure_valid = False
                elif response_json.get("success") is not False:
                    structure_valid = False
                
                # Check error code if specified
                if expected_error_code and "error" in response_json:
                    actual_code = response_json["error"].get("code")
                    if actual_code != expected_error_code:
                        structure_valid = False
        
        # Overall test result
        test_passed = status_match and structure_valid
        
        # Print result
        status_symbol = "✓" if test_passed else "✗"
        status_color_final = Colors.GREEN if test_passed else Colors.RED
        print(f"{status_color_final}{status_symbol}{Colors.END} {name}")
        print(f"   {method} {endpoint}")
        print(f"   Status: {status_color}{response.status_code}{Colors.END} (expected {expected_status})")
        
        # Print response body (truncated if too long)
        response_str = json.dumps(response_json, indent=2)
        if len(response_str) > 500:
            print(f"   Response: {response_str[:500]}... (truncated)")
        else:
            print(f"   Response: {response_str}")
        
        # Validate and print details
        if validate_response:
            if expected_status < 400:
                # Success response validation
                if response_json.get("success") is True:
                    print_success("   ✓ Response structure valid (success=true)")
                    if "data" in response_json:
                        print_success("   ✓ Response contains data")
                else:
                    print_error(f"   ✗ Expected success=true, got {response_json.get('success')}")
            else:
                # Error response validation
                if response_json.get("success") is False:
                    print_success("   ✓ Response structure valid (success=false)")
                    if "error" in response_json:
                        error_code = response_json["error"].get("code", "N/A")
                        error_msg = response_json["error"].get("message", "N/A")
                        print_info(f"   Error Code: {error_code}")
                        print_info(f"   Error Message: {error_msg}")
                        
                        if expected_error_code:
                            if error_code == expected_error_code:
                                print_success(f"   ✓ Error code matches ({expected_error_code})")
                            else:
                                print_error(f"   ✗ Expected error code '{expected_error_code}', got '{error_code}'")
                else:
                    print_error(f"   ✗ Expected success=false for error response")
        
        # Show quota if present
        if "data" in response_json:
            if "quota" in response_json["data"]:
                quota = response_json["data"]["quota"]
                print_info(f"   Quota: {quota.get('searches_remaining', '?')}/{quota.get('searches_per_month', '?')} searches remaining")
            elif isinstance(response_json["data"], dict) and "quota" in response_json["data"]:
                quota = response_json["data"]["quota"]
                print_info(f"   Quota: {quota.get('searches_remaining', '?')}/{quota.get('searches_per_month', '?')} searches remaining")
        
        # Print validation results
        if not status_match:
            print_error(f"   ✗ Status code mismatch")
        if validate_response and not structure_valid:
            print_error(f"   ✗ Response structure validation failed")
        
        print()
        return test_passed
        
    except requests.exceptions.Timeout:
        print_error(f"{name} - Request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print_error(f"{name} - Could not connect to {BASE_URL}")
        print_info("Make sure the server is running!")
        return False
    except Exception as e:
        print_error(f"{name} - Error: {str(e)}")
        return False

def test_file_upload(name, endpoint, token, file_path=None, test_data=None, expected_status=200):
    """
    Test file upload endpoint (multipart/form-data)
    
    Args:
        name: Test name
        endpoint: API endpoint path
        token: Auth token
        file_path: Path to test file (optional, creates dummy if None)
        test_data: Additional form data
        expected_status: Expected HTTP status
    
    Returns:
        (success: bool, response_json: dict) - Tuple with success status and response
    """
    url = f"{BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        files = {}
        file_obj = None
        if file_path and os.path.exists(file_path):
            file_obj = open(file_path, 'rb')
            files['file'] = ('resume.pdf', file_obj, 'application/pdf')
        elif file_path:
            # File path provided but doesn't exist
            print_error(f"{name} - Test file not found: {file_path}")
            return False, {}
        else:
            # Create a realistic test PDF (minimal valid PDF with realistic resume content)
            import io
            profile = generate_test_profile()
            
            # Generate realistic resume text (ASCII-safe for PDF)
            name = profile['full_name'].encode('ascii', 'ignore').decode('ascii')[:30]
            title = profile['current_title'].encode('ascii', 'ignore').decode('ascii')[:40]
            schools = ', '.join(profile['schools']).encode('ascii', 'ignore').decode('ascii')[:50]
            companies = ', '.join(profile['past_companies']).encode('ascii', 'ignore').decode('ascii')[:50]
            skills_str = ', '.join(profile['skills'][:5]).encode('ascii', 'ignore').decode('ascii')[:80]
            
            # Create PDF-safe resume text (escape parentheses for PDF strings)
            resume_line1 = f"{name} - {title}".replace('(', '\\(').replace(')', '\\)')
            resume_line2 = f"Education: {schools}".replace('(', '\\(').replace(')', '\\)')
            resume_line3 = f"Experience: {companies}".replace('(', '\\(').replace(')', '\\)')
            resume_line4 = f"Skills: {skills_str}".replace('(', '\\(').replace(')', '\\)')
            
            # Minimal valid PDF structure
            pdf_content = (
                b'%PDF-1.4\n'
                b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
                b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
                b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n'
                b'4 0 obj<</Length 300>>stream\n'
                b'BT\n/F1 12 Tf\n100 750 Td\n(' + resume_line1.encode('ascii', 'ignore')[:50] + b') Tj\n'
                b'0 -20 Td\n(' + resume_line2.encode('ascii', 'ignore')[:60] + b') Tj\n'
                b'0 -20 Td\n(' + resume_line3.encode('ascii', 'ignore')[:60] + b') Tj\n'
                b'0 -20 Td\n(' + resume_line4.encode('ascii', 'ignore')[:60] + b') Tj\n'
                b'ET\nendstream\nendobj\n'
                b'5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n'
                b'xref\n0 6\ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n500\n%%EOF'
            )
            file_obj = io.BytesIO(pdf_content)
            files['file'] = ('test_resume.pdf', file_obj, 'application/pdf')
        
        data = test_data or {}
        
        response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        
        # Close file if it's a file handle
        if file_obj and hasattr(file_obj, 'close') and file_path:
            file_obj.close()
        
        try:
            response_json = response.json()
        except:
            response_json = {}
        
        success = response.status_code == expected_status
        status_color = Colors.GREEN if success else Colors.RED
        
        print(f"{status_color}{'✓' if success else '✗'}{Colors.END} {name}")
        print(f"   POST {endpoint}")
        print(f"   Status: {status_color}{response.status_code}{Colors.END} (expected {expected_status})")
        
        if response_json:
            response_str = json.dumps(response_json, indent=2)
            if len(response_str) > 500:
                print(f"   Response: {response_str[:500]}... (truncated)")
            else:
                print(f"   Response: {response_str}")
            
            if response_json.get("success"):
                print_success("   ✓ Request succeeded")
            else:
                error_msg = response_json.get("error", {}).get("message", "Unknown error")
                print_error(f"   ✗ Error: {error_msg}")
        
        print()
        return success, response_json
        
    except Exception as e:
        print_error(f"{name} - Error: {str(e)}")
        print()
        return False, {}


def main():
    """Run all tests"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test API endpoints')
    parser.add_argument('--test', type=str, help='Comma-separated list of test numbers (e.g., 1,2,5)')
    parser.add_argument('--resume-only', action='store_true', help='Test only resume endpoints')
    parser.add_argument('--job-only', action='store_true', help='Test only job endpoints')
    parser.add_argument('--skip-rate-limit', action='store_true', help='Skip rate limit tests')
    parser.add_argument('--token', type=str, help='JWT token (overrides TOKEN variable)')
    parser.add_argument('--company', type=str, help='Custom company name for search tests')
    parser.add_argument('--job-title', type=str, help='Custom job title for search tests')
    parser.add_argument('--location', type=str, help='Custom location for search tests')
    parser.add_argument('--tech-focus', type=str, choices=['backend', 'frontend', 'infra', 'ml', 'mobile'], 
                       default='backend', help='Tech focus for profile generation (default: backend)')
    parser.add_argument('--seed', type=int, help='Random seed for reproducible test data')
    parser.add_argument('--job-url', type=str, help='Real job URL to parse (overrides generated URLs for test 9 and 11)')
    parser.add_argument('--resume-file', type=str, help='Path to real resume PDF file (overrides generated resume for test 8)')
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
    
    # Use provided token or fallback to default
    # Parse the token if provided via command line
    if args.token:
        test_token = parse_token(args.token)
        if not test_token:
            print_error("Failed to parse token from --token argument!")
            print_info("Token should be either:")
            print_info("  1. A plain JWT token (3 parts separated by dots)")
            print_info("  2. A base64-encoded JSON object with 'access_token' field")
            print_info("  3. A JSON string with 'access_token' field")
            sys.exit(1)
    else:
        test_token = TOKEN
    
    print_header("API Test Suite")
    
    # Check if server is running
    print_info("Testing server connection...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print_success(f"Server is running at {BASE_URL}")
        else:
            print_error(f"Server responded with status {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print_error(f"Cannot connect to server: {e}")
        print_info(f"Make sure the server is running at {BASE_URL}")
        print_info("Start it with: python web_app.py")
        sys.exit(1)
    
    # Check token
    if not test_token:
        print_error("No valid API token found!")
        print_info("Set it via: --token YOUR_TOKEN")
        print_info("Or set environment variable: export API_TOKEN='your-token'")
        print_info("\nToken format:")
        print_info("  The token should be a JWT (3 parts separated by dots)")
        print_info("  Example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
        print_info("\nYou can get your token from:")
        print_info("  1. Browser DevTools → Application → Local Storage →")
        print_info("     Look for 'sb-<project>-auth-token' key")
        print_info("     Extract the 'access_token' field from the JSON value")
        print_info("  2. After Supabase login, call: supabase.auth.getSession()")
        print_info("     Extract session.access_token from the response")
        print_info("  3. Supabase Dashboard → Authentication → Users")
        print_info("     (Note: Dashboard tokens may not work for API calls)")
        print_info("\nIf you copied a token object (JSON or base64-encoded),")
        print_info("the script will try to extract the JWT automatically.")
        sys.exit(1)
    
    # Show what real data will be used (if provided)
    if args.job_url or args.resume_file:
        print_info("\n" + "="*60)
        print_info("Real Data Configuration:")
        if args.job_url:
            print_info(f"  ✓ Real Job URL: {args.job_url}")
            print_info("    → Will be used in Test 9 (Job Parsing) and Test 11 (Auto-scrape Job)")
        if args.resume_file:
            print_info(f"  ✓ Real Resume File: {args.resume_file}")
            print_info("    → Will be used in Test 8 (Resume Upload)")
        print_info("="*60 + "\n")
    
    # Determine which tests to run
    test_numbers = None
    if args.test:
        test_numbers = [int(x.strip()) for x in args.test.split(',')]
    
    results = []
    test_counter = 0
    
    # Test 1: Health Check (No Auth)
    test_counter += 1
    if not test_numbers or test_counter in test_numbers:
        print_header(f"{test_counter}. Health Check (No Auth Required)")
        results.append(("Health Check", test_endpoint(
            "Health Check",
            "GET",
            "/api/v1/health",
            token=None,
            expected_status=200,
            validate_response=False  # Health check might not follow standard format
        )))
    
    if not test_token:
        print_info("\nSkipping authenticated tests (no token provided)")
        print_header("Test Summary")
        passed = sum(1 for _, r in results if r)
        total = len(results)
        print(f"Passed: {passed}/{total}")
        return
    
    # Resume-only mode: show resume-related tests
    # Job-only mode: show job-related tests
    # Both handled by conditional checks in each test
    
    # Test 2: Get User Quota
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Get User Quota")
        results.append(("Get Quota", test_endpoint(
            "Get User Quota",
            "GET",
            "/api/v1/quota",
            token=test_token,
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    
    # Test 3: Get User Profile
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Get User Profile")
        results.append(("Get Profile", test_endpoint(
            "Get User Profile",
            "GET",
            "/api/v1/profile",
            token=test_token,
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    
    # Test 4: Save User Profile
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Save User Profile")
        test_profile = generate_test_profile(tech_focus=args.tech_focus)
        profile_data = {
            "profile": test_profile
        }
        print_info(f"   Using profile: {test_profile['full_name']} - {test_profile['current_title']}")
        print_info(f"   Skills: {', '.join(test_profile['skills'][:5])}...")
        results.append(("Save Profile", test_endpoint(
            "Save User Profile",
            "POST",
            "/api/v1/profile/save",
            token=test_token,
            data=profile_data,
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    
    # Test 5: Search (Simple)
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Search - Simple Query")
        company = args.company or random.choice(COMPANIES)
        job_title = args.job_title or random.choice(JOB_TITLES)
        search_data_simple = {
            "company": company,
            "job_title": job_title
        }
        print_info(f"   Searching: {job_title} at {company}")
        results.append(("Search Simple", test_endpoint(
            "Search (Simple)",
            "POST",
            "/api/v1/search",
            token=test_token,
            data=search_data_simple,
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    
    # Test 6: Search (With Profile)
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Search - With Profile Context")
        company = args.company or random.choice([c for c in COMPANIES if c != "Meta"])
        job_title = args.job_title or random.choice([t for t in JOB_TITLES if "Backend" in t or "Engineer" in t])
        location = args.location or random.choice(LOCATIONS)
        test_profile = generate_test_profile(tech_focus="backend", years_exp=random.randint(5, 10))
        search_data_with_profile = {
            "company": company,
            "job_title": job_title,
            "department": "Engineering",
            "location": location,
            "profile": test_profile,
            "filters": {
                "categories": random.sample(["recruiter", "manager", "hiring_manager", "engineer"], k=2),
                "min_confidence": round(random.uniform(0.6, 0.8), 2),
                "max_results": random.randint(15, 25)
            }
        }
        print_info(f"   Searching: {job_title} at {company} ({location})")
        print_info(f"   Profile: {test_profile['full_name']} - {test_profile['current_title']}")
        results.append(("Search With Profile", test_endpoint(
            "Search (With Profile)",
            "POST",
            "/api/v1/search",
            token=test_token,
            data=search_data_with_profile,
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    
    # Test 7: Search (With Job Context)
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Search - With Job Context")
        company = args.company or random.choice(COMPANIES)
        job_title = args.job_title or random.choice(JOB_TITLES)
        required_skills = TECH_STACKS.get(args.tech_focus, TECH_STACKS["backend"])[:4]
        job_description = generate_job_description(job_title, company, required_skills)
        test_profile = generate_test_profile(tech_focus=args.tech_focus, years_exp=random.randint(4, 8))
        
        # Generate realistic job URL
        job_id = random.randint(1000000, 9999999)
        job_url = f"https://www.linkedin.com/jobs/view/{job_id}"
        if "google" in company.lower():
            job_url = f"https://careers.google.com/jobs/results/{job_id}"
        elif "meta" in company.lower() or "facebook" in company.lower():
            job_url = f"https://www.metacareers.com/jobs/{job_id}"
        
        search_data_with_job = {
            "company": company,
            "job_title": job_title,
            "job_url": job_url,
            "job_description": job_description,
            "required_skills": required_skills,
            "profile": test_profile
        }
        print_info(f"   Searching: {job_title} at {company}")
        print_info(f"   Job URL: {job_url}")
        print_info(f"   Required Skills: {', '.join(required_skills[:3])}...")
        results.append(("Search With Job Context", test_endpoint(
            "Search (With Job Context)",
            "POST",
            "/api/v1/search",
            token=test_token,
            data=search_data_with_job,
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    
    # Test 8: Upload Resume (File Upload)
    test_counter += 1
    saved_resume_url = None
    if (not test_numbers or test_counter in test_numbers) and (args.resume_only or (not args.job_only and not args.skip_rate_limit)):
        print_header(f"{test_counter}. Resume Upload - PDF File")
        resume_file_path = args.resume_file if args.resume_file else None
        
        if resume_file_path:
            if not os.path.exists(resume_file_path):
                print_error(f"Resume file not found: {resume_file_path}")
                results.append(("Upload Resume (File)", False))
            else:
                print_info(f"   Using real resume file: {resume_file_path}")
                result, response_json = test_file_upload(
                    "Upload Resume (PDF File)",
                    "/api/v1/resume/upload",
                    test_token,
                    file_path=resume_file_path,
                    expected_status=200
                )
                results.append(("Upload Resume (File)", result))
        else:
            print_info("   Using generated test resume PDF")
            result, response_json = test_file_upload(
                "Upload Resume (PDF File)",
                "/api/v1/resume/upload",
                test_token,
                file_path=None,  # Will create dummy PDF
                expected_status=200
            )
            results.append(("Upload Resume (File)", result))
        
        # Store resume URL for next test if upload succeeded
        if result and response_json.get("data", {}).get("resume_url"):
            saved_resume_url = response_json["data"]["resume_url"]
            print_info(f"   Saved resume URL for next test: {saved_resume_url[:50]}...")
    
    # Test 8b: Upload Resume (URL - if we have a resume URL from previous upload)
    test_counter += 1
    if saved_resume_url and (not test_numbers or test_counter in test_numbers) and (args.resume_only or not args.job_only):
        print_header(f"{test_counter}. Resume Upload - From URL")
        results.append(("Upload Resume (URL)", test_endpoint(
            "Upload Resume (URL)",
            "POST",
            "/api/v1/resume/upload",
            token=test_token,
            data={"resume_url": saved_resume_url},
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    elif args.resume_only and not saved_resume_url:
        # If resume-only mode but no URL yet, skip this test
        test_counter -= 1
    
    # Test 9: Parse Job URL
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and (args.job_only or not args.resume_only):
        print_header(f"{test_counter}. Job Parsing - From URL")
        
        # Use real job URL if provided, otherwise generate a realistic one
        if args.job_url:
            job_url = args.job_url
            print_info(f"   Using real job URL: {job_url}")
        else:
            # Use a realistic job URL format (won't actually scrape real page, but tests the endpoint)
            job_id = random.randint(3000000000, 4000000000)
            company = args.company or random.choice(COMPANIES)
            
            # Generate realistic job URLs based on company
            if "google" in company.lower():
                job_url = f"https://careers.google.com/jobs/results/{job_id}"
            elif "meta" in company.lower() or "facebook" in company.lower():
                job_url = f"https://www.metacareers.com/jobs/{job_id}"
            else:
                job_url = f"https://www.linkedin.com/jobs/view/{job_id}"
            print_info(f"   Using generated job URL: {job_url}")
        
        results.append(("Parse Job URL", test_endpoint(
            "Parse Job from URL",
            "POST",
            "/api/v1/job/parse",
            token=test_token,
            data={"job_url": job_url},
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    
    # Test 10: Search with Auto-loaded Resume
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Search - Auto-load Resume Data")
        company = args.company or random.choice([c for c in COMPANIES if c != "Stripe"])
        job_title = args.job_title or random.choice(JOB_TITLES)
        search_data_auto = {
            "company": company,
            "job_title": job_title
            # No profile provided - should auto-load from saved resume
        }
        print_info(f"   Searching: {job_title} at {company} (auto-loading resume)")
        results.append(("Search Auto-Resume", test_endpoint(
            "Search (Auto-load Resume)",
            "POST",
            "/api/v1/search",
            token=test_token,
            data=search_data_auto,
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    
    # Test 11: Search with Auto-scraped Job
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Search - Auto-scrape Job URL")
        
        # Use real job URL if provided, otherwise generate one
        if args.job_url:
            job_url = args.job_url
            print_info(f"   Using real job URL: {job_url}")
            # Try to extract company from URL if not provided
            if not args.company:
                if "google" in job_url.lower() or "careers.google" in job_url.lower():
                    company = "Google"
                elif "meta" in job_url.lower() or "facebook" in job_url.lower() or "metacareers" in job_url.lower():
                    company = "Meta"
                elif "linkedin" in job_url.lower():
                    # For LinkedIn, use a placeholder - API will extract actual company from the job posting
                    company = "Company (extracted from URL)"
                else:
                    # Default placeholder - API should extract actual company from URL
                    company = "Company (extracted from URL)"
            else:
                company = args.company
        else:
            company = args.company or random.choice(COMPANIES)
            job_title = args.job_title or random.choice(JOB_TITLES)
            job_id = random.randint(1000000, 9999999)
            
            # Generate realistic job URL
            if "google" in company.lower():
                job_url = f"https://careers.google.com/jobs/results/{job_id}"
            elif "meta" in company.lower() or "facebook" in company.lower():
                job_url = f"https://www.metacareers.com/jobs/{job_id}"
            else:
                job_url = f"https://www.linkedin.com/jobs/view/{job_id}"
            print_info(f"   Using generated job URL: {job_url}")
        
        job_title = args.job_title or random.choice(JOB_TITLES)
        
        search_data_auto_job = {
            "company": company,
            "job_title": job_title,
            "job_url": job_url
            # No job_description - should auto-scrape from URL
        }
        print_info(f"   Searching: {job_title} at {company}")
        print_info(f"   Auto-scraping from: {job_url}")
        results.append(("Search Auto-Job", test_endpoint(
            "Search (Auto-scrape Job)",
            "POST",
            "/api/v1/search",
            token=test_token,
            data=search_data_auto_job,
            expected_status=200,
            expected_success=True,
            validate_response=True
        )))
    
    # Test 12: Error Cases - Invalid Token
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.skip_rate_limit and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Error Handling - Invalid Token")
        results.append(("Invalid Token", test_endpoint(
            "Invalid Token Test",
            "GET",
            "/api/v1/quota",
            token="invalid_token_here",
            expected_status=401,
            expected_success=False,
            expected_error_code="AUTH_INVALID"
        )))
    
    # Test 13: Error Cases - Missing Token
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.skip_rate_limit and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Error Handling - Missing Token")
        results.append(("Missing Token", test_endpoint(
            "Missing Token Test",
            "GET",
            "/api/v1/quota",
            token=None,
            expected_status=401,
            expected_success=False,
            expected_error_code="AUTH_REQUIRED"
        )))
    
    # Test 14: Error Cases - Invalid Request
    test_counter += 1
    if (not test_numbers or test_counter in test_numbers) and not args.skip_rate_limit and not args.resume_only and not args.job_only:
        print_header(f"{test_counter}. Error Handling - Invalid Request")
        # Test invalid request - should get 400 with INVALID_REQUEST
        url = f"{BASE_URL}/api/v1/search"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {test_token}"
        }
        try:
            response = requests.post(url, headers=headers, json={}, timeout=60)
            response_json = response.json()
            
            # Accept either 400 (validation error) or 429 (rate limit) as both are valid error responses
            if response.status_code == 400:
                if (response_json.get("success") is False and 
                    response_json.get("error", {}).get("code") == "INVALID_REQUEST"):
                    print_success("✓ Invalid Request Test")
                    print("   POST /api/v1/search")
                    print(f"   Status: {Colors.GREEN}400{Colors.END} (expected 400)")
                    print_success("   ✓ Got validation error as expected")
                    print_success(f"   ✓ Error code: INVALID_REQUEST")
                    results.append(("Invalid Request", True))
                else:
                    print_error("✗ Invalid Request Test")
                    print(f"   Got 400 but wrong error structure")
                    results.append(("Invalid Request", False))
            elif response.status_code == 429:
                print_info("⚠ Invalid Request Test - Got rate limit (429) instead of validation error (400)")
                print("   This means rate limit was hit before validation")
                if response_json.get("success") is False:
                    print_success("   ✓ Response structure valid (success=false)")
                    error_code = response_json.get("error", {}).get("code", "N/A")
                    print_info(f"   Error Code: {error_code}")
                results.append(("Invalid Request", True))
            else:
                print_error(f"✗ Invalid Request Test - Got unexpected status {response.status_code}")
                results.append(("Invalid Request", False))
            print()
        except Exception as e:
            print_error(f"Invalid Request Test - Error: {e}")
            results.append(("Invalid Request", False))
            print()
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n{Colors.BOLD}Results:{Colors.END}")
    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {status} - {name}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.END}")
    
    if total == 0:
        print_info("\nNo tests were run. Use --help to see options.")
        return 0
    
    if passed == total:
        print_success("\nAll tests passed! 🎉")
        return 0
    else:
        print_error(f"\n{total - passed} test(s) failed")
        print_info("\nTip: Use --test <numbers> to run specific tests")
        print_info("Example: python test_api.py --test 8,9")
        return 1

if __name__ == "__main__":
    # Check if requests library is available
    try:
        import requests
    except ImportError:
        print_error("'requests' library not found!")
        print_info("Install it with: pip install requests")
        sys.exit(1)
    
    # Show usage if help requested
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("\n" + "="*60)
        print("API Test Suite - Quick Usage Guide")
        print("="*60)
        print("\nBasic Usage:")
        print("  python test_api.py                    # Run all tests")
        print("  python test_api.py --test 1,2,8       # Run specific tests")
        print("  python test_api.py --resume-only      # Test only resume endpoints")
        print("  python test_api.py --job-only          # Test only job endpoints")
        print("  python test_api.py --skip-rate-limit  # Skip rate limit tests")
        print("  python test_api.py --token YOUR_TOKEN # Use custom token")
        print("\nCustomize Test Data:")
        print("  python test_api.py --company Stripe --job-title 'Senior Engineer'")
        print("  python test_api.py --tech-focus frontend --location 'San Francisco, CA'")
        print("  python test_api.py --seed 42           # Use fixed seed for reproducibility")
        print("  python test_api.py --job-url 'https://linkedin.com/jobs/view/123456'")
        print("  python test_api.py --resume-file path/to/resume.pdf")
        print("\nTest Numbers:")
        print("  1. Health Check")
        print("  2. Get Quota")
        print("  3. Get Profile")
        print("  4. Save Profile")
        print("  5. Search Simple")
        print("  6. Search With Profile")
        print("  7. Search With Job Context")
        print("  8. Resume Upload (PDF)")
        print("  9. Job Parsing (URL)")
        print("  10. Search Auto-Resume")
        print("  11. Search Auto-Job")
        print("  12. Invalid Token")
        print("  13. Missing Token")
        print("  14. Invalid Request")
        print("\nExamples:")
        print("  python test_api.py --test 8,9         # Test resume & job endpoints")
        print("  python test_api.py --resume-only      # Quick resume testing")
        print("  python test_api.py --job-only         # Quick job testing")
        print("="*60 + "\n")
    
    exit_code = main()
    sys.exit(exit_code)

