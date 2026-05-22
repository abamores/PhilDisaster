#!/bin/bash
# Telegram Bot Setup Helper
# Run this script to configure your Telegram bot for disaster alerts

echo "=================================================="
echo "  📱 Philippine Disaster Monitor - Telegram Setup"
echo "=================================================="
echo ""

# Check if token already set
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    echo "✅ BOT_TOKEN already set in environment"
fi

echo ""
echo "To set up Telegram alerts, you need:"
echo ""
echo "1. BOT TOKEN - Get from @BotFather on Telegram"
echo "   - Open Telegram and search for @BotFather"
echo "   - Send /newbot and follow instructions"
echo "   - Copy the token it gives you"
echo ""
echo "2. YOUR CHAT ID - Get by messaging @userinfobot"
echo "   - Open Telegram and search for @userinfobot"
echo "   - Send any message"
echo "   - It will reply with your numeric chat ID"
echo ""
echo "=================================================="
echo ""

# Interactive setup
read -p "Enter your Telegram Bot Token: " bot_token
read -p "Enter your Chat ID: " chat_id

# Save to config file
cat > config.json << EOF
{
  "telegram_bot_token": "$bot_token",
  "telegram_chat_id": "$chat_id"
}
EOF

echo ""
echo "✅ Configuration saved to config.json"
echo ""
echo "You can also set these as environment variables:"
echo "  export TELEGRAM_BOT_TOKEN='$bot_token'"
echo "  export TELEGRAM_CHAT_ID='$chat_id'"
echo ""
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Test the monitor: python monitor.py --once"
echo "  2. Run the dashboard: streamlit run dashboard.py"
echo "  3. Run continuous monitoring: python monitor.py --interval 15"
echo ""