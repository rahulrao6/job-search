#!/bin/bash
# Verify the project is ready for Render.com deployment

echo "🔍 Verifying Render.com Deployment Readiness"
echo "=============================================="
echo ""

# Check 1: Render files exist
echo "✅ Check 1: Render files exist"
if [ -f "render.yaml" ] && [ -f "RENDER_SETUP.md" ]; then
    echo "   ✓ render.yaml found"
    echo "   ✓ RENDER_SETUP.md found"
else
    echo "   ✗ Missing Render files!"
    exit 1
fi
echo ""

# Check 2: Replit files removed
echo "✅ Check 2: Replit files removed"
if [ ! -f ".replit" ] && [ ! -f "replit.nix" ] && [ ! -f "REPLIT_SETUP.md" ]; then
    echo "   ✓ .replit not found (good)"
    echo "   ✓ replit.nix not found (good)"
    echo "   ✓ REPLIT_SETUP.md not found (good)"
else
    echo "   ✗ Replit files still exist!"
    exit 1
fi
echo ""

# Check 3: web_app.py configured correctly
echo "✅ Check 3: web_app.py configuration"
if grep -q "PORT" web_app.py && grep -q "0.0.0.0" web_app.py; then
    echo "   ✓ PORT environment variable used"
    echo "   ✓ Host set to 0.0.0.0"
else
    echo "   ✗ web_app.py not configured correctly!"
    exit 1
fi
echo ""

# Check 4: requirements.txt has Flask
echo "✅ Check 4: Dependencies"
if grep -q "Flask" requirements.txt; then
    echo "   ✓ Flask in requirements.txt"
else
    echo "   ✗ Flask missing from requirements.txt!"
    exit 1
fi
echo ""

# Check 5: No Replit references in code
echo "✅ Check 5: No Replit references in code"
REPLIT_COUNT=$(grep -r "replit" --include="*.py" -i . 2>/dev/null | grep -v ".git/" | grep -v "RENDER" | wc -l | tr -d ' ')
if [ "$REPLIT_COUNT" -eq "0" ]; then
    echo "   ✓ No Replit references in Python code"
else
    echo "   ⚠️  Found $REPLIT_COUNT Replit references in Python code"
fi
echo ""

# Check 6: Git status
echo "✅ Check 6: Git status"
if git status --short | grep -q "RENDER"; then
    echo "   ✓ New Render files ready to commit"
else
    echo "   ⚠️  No new Render files to commit"
fi
echo ""

echo "🎉 ALL CHECKS PASSED!"
echo ""
echo "📋 Next Steps:"
echo "1. Test locally: python web_app.py"
echo "2. Commit changes: git add . && git commit -m 'Migrate to Render.com'"
echo "3. Push to GitHub: git push origin main"
echo "4. Deploy to Render: Follow RENDER_SETUP.md"
echo ""
echo "🚀 Ready to deploy!"
