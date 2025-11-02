# Troubleshooting Guide

## Common Issues and Fixes

### 1. Resume Upload Errors

#### Error: "Failed to upload resume to storage: SyncBucketActionsMixin.upload() got an unexpected keyword argument 'upsert'"

**Status:** ✅ FIXED - The storage upload function now handles file overwrites correctly without the unsupported `upsert` parameter.

#### Error: "pdfplumber extraction failed: No module named 'pdfplumber'"

**Fix:**
```bash
pip install pdfplumber
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

**Note:** The system will automatically fall back to PyPDF2 if pdfplumber is not installed, but pdfplumber provides better extraction quality.

#### Error: OpenAI API Quota Exceeded (429 error)

**What happened:** Your OpenAI API key has exceeded its quota or billing limits.

**Solutions:**

1. **Check your OpenAI billing:**
   - Visit: https://platform.openai.com/account/billing
   - Add payment method or increase quota

2. **Verify your API key:**
   - Visit: https://platform.openai.com/api-keys
   - Make sure your key is active and starts with `sk-`

3. **The system will continue working without AI:**
   - Resume parsing will use pattern-based extraction
   - Job parsing will use pattern-based extraction
   - You'll get results, just without AI enhancement

**How to add/update your OpenAI API key:**

```bash
# In your .env file
OPENAI_API_KEY=sk-your-actual-key-here
```

**Format requirements:**
- Must start with `sk-`
- Should be 51+ characters long
- Get a new key from: https://platform.openai.com/api-keys

### 2. OpenAI API Key Issues

#### Error: "OpenAI API key format invalid"

**Cause:** Your API key doesn't start with `sk-` or is malformed.

**Fix:**
1. Get a new key from https://platform.openai.com/api-keys
2. Update your `.env` file:
   ```bash
   OPENAI_API_KEY=sk-proj-...your-key-here
   ```
3. Restart your server

#### Error: "OpenAI API key invalid or expired"

**Fix:**
1. Verify your key is active at https://platform.openai.com/api-keys
2. Make sure you copied the full key (starts with `sk-`)
3. Check that you have billing set up
4. Try creating a new API key

### 3. Verifying Your Setup

Run the verification script:

```bash
python verify_setup.py
```

This will check:
- ✅ All required Python packages are installed
- ✅ Environment variables are set correctly
- ✅ OpenAI API key format and connection
- ✅ Supabase configuration

### 4. System Behavior Without OpenAI

**The system works perfectly fine without OpenAI!**

**What still works:**
- ✅ Resume PDF text extraction (pdfplumber/PyPDF2)
- ✅ Pattern-based resume parsing (skills, companies, schools)
- ✅ Job posting parsing (pattern-based)
- ✅ All search functionality
- ✅ Profile matching

**What's disabled:**
- ❌ AI-enhanced extraction (falls back to patterns)
- ❌ AI categorization (uses basic rules)

**Performance:**
- Pattern-based parsing is fast and reliable
- Results are good, just not as sophisticated as AI-enhanced

### 5. Installing Missing Dependencies

If you see import errors:

```bash
# Activate your virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install all dependencies
pip install -r requirements.txt

# Or install specific packages
pip install pdfplumber openai supabase flask
```

### 6. Environment Variables Setup

Create a `.env` file in the project root:

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Optional but recommended
OPENAI_API_KEY=sk-your-key-here

# Optional
GOOGLE_API_KEY=your-key
GOOGLE_CSE_ID=your-cse-id
GITHUB_TOKEN=your-token
```

Then load them in your shell:

```bash
# Load .env file
export $(cat .env | xargs)

# Or use python-dotenv (automatic if using Flask)
```

## Getting Help

1. **Check the verification script:**
   ```bash
   python verify_setup.py
   ```

2. **Check server logs** for detailed error messages

3. **Verify your API keys** are active and have quota:
   - OpenAI: https://platform.openai.com/account/billing
   - Supabase: https://app.supabase.com/

4. **Review the error messages** - they now include helpful hints and links

## Quick Fix Checklist

- [ ] Run `pip install -r requirements.txt`
- [ ] Verify `.env` file exists with correct variables
- [ ] Check OpenAI API key format (must start with `sk-`)
- [ ] Verify OpenAI billing is set up
- [ ] Run `python verify_setup.py`
- [ ] Restart your server after making changes

## System Resilience

The system is designed to be resilient:

1. **Graceful degradation:** If OpenAI fails, it falls back to pattern-based parsing
2. **Multiple PDF parsers:** Falls back from pdfplumber to PyPDF2
3. **Clear error messages:** Tells you exactly what's wrong and how to fix it
4. **Automatic disable:** Disables problematic features to avoid repeated errors

Even if OpenAI is down or your quota is exceeded, the system will continue working with pattern-based extraction.

