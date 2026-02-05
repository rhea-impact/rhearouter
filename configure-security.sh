#!/bin/bash
# Security configuration script for RheaRouter

set -e

echo "=== RheaRouter Security Configuration ==="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi

# Ask about API key authentication
echo "Do you want to enable API key authentication? (recommended for shared access)"
echo "1) Yes - Generate and enable API keys"
echo "2) No - Keep authentication disabled (only you using it)"
read -p "Choice [1/2]: " auth_choice

if [ "$auth_choice" = "1" ]; then
    echo ""
    echo "Generating 3 secure API keys..."

    # Generate keys
    KEY1=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    KEY2=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    KEY3=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

    # Add to .env
    if grep -q "^API_KEYS=" .env; then
        sed -i "s/^API_KEYS=.*/API_KEYS=$KEY1,$KEY2,$KEY3/" .env
    else
        echo "" >> .env
        echo "# API Authentication" >> .env
        echo "API_KEYS=$KEY1,$KEY2,$KEY3" >> .env
    fi

    if grep -q "^FEATURE_AUTH=" .env; then
        sed -i "s/^FEATURE_AUTH=.*/FEATURE_AUTH=true/" .env
    else
        echo "FEATURE_AUTH=true" >> .env
    fi

    echo ""
    echo "✓ API keys generated and saved to .env"
    echo ""
    echo "Your API keys (save these securely):"
    echo "  Key 1: $KEY1"
    echo "  Key 2: $KEY2"
    echo "  Key 3: $KEY3"
    echo ""
else
    echo "✓ Authentication disabled"
fi

# Configure firewall
echo ""
echo "Configuring firewall to restrict access to Tailscale network..."
sudo ufw allow from 100.0.0.0/8 to any port 8000 comment 'RheaRouter Tailscale' 2>/dev/null || true
echo "✓ Firewall configured"

# Show current rate limits
echo ""
echo "Current rate limits (from .env):"
grep -E "^(GLOBAL_RATE_LIMIT|PER_CLIENT_RATE_LIMIT)" .env || echo "  Using defaults"

echo ""
read -p "Do you want to adjust rate limits? [y/N]: " adjust_limits

if [[ "$adjust_limits" =~ ^[Yy]$ ]]; then
    read -p "Global limit (requests/min) [60]: " global_limit
    global_limit=${global_limit:-60}

    read -p "Per-client limit (requests/min) [20]: " client_limit
    client_limit=${client_limit:-20}

    if grep -q "^GLOBAL_RATE_LIMIT=" .env; then
        sed -i "s/^GLOBAL_RATE_LIMIT=.*/GLOBAL_RATE_LIMIT=$global_limit/" .env
    else
        echo "GLOBAL_RATE_LIMIT=$global_limit" >> .env
    fi

    if grep -q "^PER_CLIENT_RATE_LIMIT=" .env; then
        sed -i "s/^PER_CLIENT_RATE_LIMIT=.*/PER_CLIENT_RATE_LIMIT=$client_limit/" .env
    else
        echo "PER_CLIENT_RATE_LIMIT=$client_limit" >> .env
    fi

    echo "✓ Rate limits updated"
fi

# Restart service
echo ""
echo "Restarting RheaRouter to apply changes..."
sudo systemctl restart rhearouter.service
sleep 2

# Verify
echo ""
echo "=== Security Configuration Complete ==="
echo ""
echo "Current status:"
sudo systemctl status rhearouter.service --no-pager | head -10

echo ""
echo "Testing health endpoint..."
curl -s http://localhost:8000/health | python3 -m json.tool

echo ""
echo "✅ Security configuration complete!"
echo ""
echo "Next steps:"
if [ "$auth_choice" = "1" ]; then
    echo "  1. Save your API keys securely"
    echo "  2. Test with: curl -H 'Authorization: Bearer KEY' http://100.87.176.89:8000/health"
fi
echo "  3. Review security guide: cat SECURITY_SETUP.md"
echo "  4. Monitor logs: sudo journalctl -u rhearouter -f"
