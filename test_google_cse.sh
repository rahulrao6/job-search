#!/bin/bash

# Test script for Google CSE setup
# Usage: ./test_google_cse.sh YOUR_API_KEY_HERE

if [ -z "$1" ]; then
    echo "Usage: ./test_google_cse.sh YOUR_API_KEY"
    echo ""
    echo "Example:"
    echo "  ./test_google_cse.sh AIzaSyABCDEF123456..."
    exit 1
fi

CSE_ID="57a851efab97f4477"
API_KEY="$1"

echo "🧪 Testing Google Custom Search Engine..."
echo "=========================================="
echo ""
echo "CSE ID: $CSE_ID"
echo "API Key: ${API_KEY:0:10}...${API_KEY: -5}"
echo ""

# Test the API
curl -s "https://www.googleapis.com/customsearch/v1?key=$API_KEY&cx=$CSE_ID&q=test" > /tmp/cse_test.json

# Check result
if grep -q '"searchInformation"' /tmp/cse_test.json; then
    echo "✅ SUCCESS! Google CSE is working!"
    echo ""
    echo "Now add to .env file:"
    echo "  echo 'GOOGLE_CSE_ID=$CSE_ID' >> .env"
    echo "  echo 'GOOGLE_API_KEY=$API_KEY' >> .env"
    echo ""
    echo "Or manually edit .env and add:"
    echo "  GOOGLE_CSE_ID=$CSE_ID"
    echo "  GOOGLE_API_KEY=$API_KEY"
else
    echo "❌ ERROR!"
    echo ""
    cat /tmp/cse_test.json | head -20
    echo ""
    echo "Common issues:"
    echo "  1. Make sure Custom Search API is enabled"
    echo "  2. Make sure API key is correct"
    echo "  3. Check https://console.cloud.google.com/apis/library"
fi

rm -f /tmp/cse_test.json
