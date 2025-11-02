#!/bin/bash

# Simple bash script to test API endpoints
# Usage: ./test_api.sh [YOUR_JWT_TOKEN]

BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TOKEN="${1:-${API_TOKEN}}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}API Test Script${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if token provided
if [ -z "$TOKEN" ]; then
    echo -e "${YELLOW}⚠ No token provided${NC}"
    echo "Usage: ./test_api.sh YOUR_JWT_TOKEN"
    echo "Or set: export API_TOKEN='your-token'"
    echo ""
    echo "Testing unauthenticated endpoints only...\n"
    SKIP_AUTH=true
else
    echo -e "${GREEN}✓ Token provided${NC}\n"
    SKIP_AUTH=false
fi

# Test 1: Health Check
echo -e "${BLUE}1. Health Check${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/health")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Status: $HTTP_CODE${NC}"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}✗ Status: $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

if [ "$SKIP_AUTH" = true ]; then
    echo -e "${YELLOW}Skipping authenticated tests...${NC}"
    exit 0
fi

# Test 2: Get Quota
echo -e "${BLUE}2. Get User Quota${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$BASE_URL/api/v1/quota")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Status: $HTTP_CODE${NC}"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}✗ Status: $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

# Test 3: Get Profile
echo -e "${BLUE}3. Get User Profile${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$BASE_URL/api/v1/profile")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Status: $HTTP_CODE${NC}"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}✗ Status: $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

# Test 4: Search (Simple)
echo -e "${BLUE}4. Search - Simple${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"company": "Stripe", "job_title": "Software Engineer"}' \
    "$BASE_URL/api/v1/search")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Status: $HTTP_CODE${NC}"
    echo "$BODY" | jq '.data.results.total_found, .data.results.category_counts' 2>/dev/null || echo "$BODY" | head -20
else
    echo -e "${RED}✗ Status: $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

# Test 5: Search (With Profile)
echo -e "${BLUE}5. Search - With Profile${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "company": "Meta",
        "job_title": "Backend Engineer",
        "profile": {
            "skills": ["Python", "Go"],
            "past_companies": ["Google"],
            "schools": ["Stanford"]
        }
    }' \
    "$BASE_URL/api/v1/search")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Status: $HTTP_CODE${NC}"
    echo "$BODY" | jq '.data.results.total_found, .data.insights' 2>/dev/null || echo "$BODY" | head -20
else
    echo -e "${RED}✗ Status: $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

echo -e "${GREEN}Tests completed!${NC}"

