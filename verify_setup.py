#!/usr/bin/env python3
"""Verify setup and check for common issues"""

import os
import sys

def check_module(module_name, install_cmd=None):
    """Check if a module is installed"""
    try:
        __import__(module_name)
        return True, None
    except ImportError:
        return False, install_cmd or f"pip install {module_name}"

def check_env_var(var_name, description="", required=False, format_hint=""):
    """Check if environment variable is set and valid"""
    value = os.getenv(var_name)
    if not value:
        if required:
            return False, f"{var_name} is REQUIRED. {description}"
        else:
            return None, f"{var_name} is optional. {description}"
    
    # Validate OpenAI key format
    if var_name == "OPENAI_API_KEY":
        if not value.startswith("sk-"):
            return False, f"OPENAI_API_KEY format invalid (should start with 'sk-'). Current value: {value[:10]}..."
        else:
            return True, f"OPENAI_API_KEY format looks valid"
    
    return True, f"{var_name} is set"

def main():
    print("=" * 60)
    print("🔍 Job Search System - Setup Verification")
    print("=" * 60)
    print()
    
    issues = []
    warnings = []
    
    # Check Python version
    print("📦 Python Environment")
    print(f"   Python version: {sys.version.split()[0]}")
    print()
    
    # Check required modules
    print("📚 Required Modules")
    modules = [
        ("pdfplumber", "pip install pdfplumber"),
        ("PyPDF2", "pip install PyPDF2"),
        ("openai", "pip install openai"),
        ("supabase", "pip install supabase"),
        ("flask", "pip install flask"),
    ]
    
    for module, install_cmd in modules:
        installed, error = check_module(module)
        if installed:
            print(f"   ✅ {module}")
        else:
            print(f"   ❌ {module} - MISSING")
            print(f"      Install with: {install_cmd}")
            issues.append(f"Missing module: {module}")
    print()
    
    # Check environment variables
    print("🔑 Environment Variables")
    
    # Required
    required_vars = [
        ("SUPABASE_URL", "Required for database", True),
        ("SUPABASE_KEY", "Required for database authentication", True),
    ]
    
    optional_vars = [
        ("OPENAI_API_KEY", "Optional - For AI-enhanced parsing (should start with 'sk-')", False, "sk-..."),
    ]
    
    for var_name, description, required, *rest in required_vars + optional_vars:
        result, message = check_env_var(var_name, description, required)
        if result is True:
            print(f"   ✅ {var_name}")
        elif result is False:
            print(f"   ❌ {var_name}: {message}")
            issues.append(message)
        else:
            print(f"   ⚠️  {var_name}: {message}")
            warnings.append(message)
    print()
    
    # Test OpenAI if key is set
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key.startswith("sk-"):
        print("🧪 Testing OpenAI Connection")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            # Try a simple API call
            response = client.models.list()
            print("   ✅ OpenAI connection successful")
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                print("   ⚠️  OpenAI quota exceeded")
                print("      Check billing: https://platform.openai.com/account/billing")
                warnings.append("OpenAI quota exceeded")
            elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                print("   ❌ OpenAI API key invalid")
                print("      Verify your key at: https://platform.openai.com/api-keys")
                issues.append("OpenAI API key invalid")
            else:
                print(f"   ⚠️  OpenAI connection error: {error_msg}")
                warnings.append(f"OpenAI error: {error_msg}")
    print()
    
    # Summary
    print("=" * 60)
    print("📋 Summary")
    print("=" * 60)
    
    if not issues and not warnings:
        print("✅ All checks passed! Your system is ready to use.")
        return 0
    else:
        if issues:
            print("\n❌ CRITICAL ISSUES (must fix):")
            for issue in issues:
                print(f"   • {issue}")
        
        if warnings:
            print("\n⚠️  WARNINGS (system will work but may have limited functionality):")
            for warning in warnings:
                print(f"   • {warning}")
        
        print("\n💡 TIP: The system will work without OpenAI, but AI-enhanced parsing will be disabled.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

