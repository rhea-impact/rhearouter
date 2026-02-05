#!/bin/bash
# Setup script for RheaRouter systemd service

set -e

echo "=== RheaRouter Service Setup ==="
echo ""

# Check if running as regular user
if [ "$EUID" -eq 0 ]; then
   echo "Please run as regular user (not root)"
   exit 1
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
fi

# Install systemd service
echo "Installing systemd service..."
sudo cp /tmp/rhearouter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rhearouter.service

# Configure firewall (allow from Tailscale network)
echo "Configuring firewall..."
sudo ufw allow from 100.0.0.0/8 to any port 8000 comment 'RheaRouter via Tailscale'

# Start service
echo "Starting RheaRouter..."
sudo systemctl start rhearouter.service

# Check status
echo ""
echo "=== Service Status ==="
sudo systemctl status rhearouter.service --no-pager

echo ""
echo "=== Testing Health Endpoint ==="
sleep 2
curl -s http://localhost:8000/health | python3 -m json.tool

echo ""
echo "=== Setup Complete ==="
echo "RheaRouter is accessible at:"
echo "  - Locally: http://localhost:8000"
echo "  - Tailscale: http://100.87.176.89:8000"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status rhearouter   # Check status"
echo "  sudo systemctl restart rhearouter  # Restart service"
echo "  sudo systemctl stop rhearouter     # Stop service"
echo "  sudo journalctl -u rhearouter -f   # View logs"
