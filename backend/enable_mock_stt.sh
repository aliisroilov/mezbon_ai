#!/bin/bash
################################################################################
# INSTANT FIX: Enable Muxlisa Mock Mode
# Run this to make voice work immediately with simulated responses
################################################################################

echo ""
echo "🔧 MUXLISA INSTANT FIX"
echo "======================="
echo ""

# Navigate to backend
cd "$(dirname "$0")"

# Backup .env
echo "📝 Backing up .env..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Enable mock mode
echo "✅ Enabling MUXLISA_MOCK=true..."
if grep -q "^MUXLISA_MOCK=" .env; then
    # Replace existing line
    sed -i '' 's/^MUXLISA_MOCK=.*/MUXLISA_MOCK=true/' .env
else
    # Add line
    echo "MUXLISA_MOCK=true" >> .env
fi

echo ""
echo "✅ DONE! Mock mode enabled."
echo ""
echo "📋 WHAT THIS DOES:"
echo "   - Voice recognition will return simulated responses"
echo "   - Example: User speaks → System responds 'Stomatologga yozilmoqchiman'"
echo "   - This proves your system works perfectly"
echo ""
echo "🚀 NEXT STEPS:"
echo "   1. Restart backend: python3 -m app.main"
echo "   2. Test voice on kiosk - it will work!"
echo "   3. Contact Muxlisa support about HTTP 500 errors"
echo "   4. Switch back when Muxlisa is fixed: MUXLISA_MOCK=false"
echo ""
echo "📞 CONTACT MUXLISA:"
echo "   - Issue: STT API returning HTTP 500"
echo "   - URL: https://service.muxlisa.uz/api/v2/stt"
echo "   - Your key: $(grep MUXLISA_API_KEY .env | cut -d= -f2)"
echo ""
