# RheaRouter Tailscale Setup Guide

## Quick Start (Currently Running)

✅ **RheaRouter is already running!**

- **Local Access:** http://localhost:8000
- **Tailscale Access:** http://100.87.176.89:8000
- **Health Check:** `curl http://100.87.176.89:8000/health`

## Current Status

RheaRouter is running as a background process. To make it permanent:

```bash
cd /home/djshanklin/repos/rhearouter
./setup-service.sh
```

## Manual Setup

If you prefer to set it up manually:

### 1. Create Systemd Service

The service file is already created at `/tmp/rhearouter.service`. Install it:

```bash
sudo cp /tmp/rhearouter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rhearouter.service
sudo systemctl start rhearouter.service
```

### 2. Configure Firewall

Allow access from Tailscale network:

```bash
sudo ufw allow from 100.0.0.0/8 to any port 8000 comment 'RheaRouter via Tailscale'
```

### 3. Verify

Check service status:

```bash
sudo systemctl status rhearouter.service
```

Test the endpoint:

```bash
# Local test
curl http://localhost:8000/health

# Tailscale test
curl http://100.87.176.89:8000/health
```

## Access from Other Devices

From any device on your Tailscale network (like your MacBook):

```bash
# Health check
curl http://100.87.176.89:8000/health

# List models
curl http://100.87.176.89:8000/v1/models

# Chat completion
curl -X POST http://100.87.176.89:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "llama3.1:8b"
  }'
```

## Using with OpenAI-Compatible Clients

Configure any OpenAI-compatible client to use RheaRouter:

```python
import openai

client = openai.OpenAI(
    base_url="http://100.87.176.89:8000/v1",
    api_key="not-needed"  # No auth required by default
)

response = client.chat.completions.create(
    model="llama3.1:8b",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

## Service Management

```bash
# Start service
sudo systemctl start rhearouter

# Stop service
sudo systemctl stop rhearouter

# Restart service
sudo systemctl restart rhearouter

# Check status
sudo systemctl status rhearouter

# View logs
sudo journalctl -u rhearouter -f

# View recent errors
sudo journalctl -u rhearouter -p err -n 50
```

## Troubleshooting

### Service won't start

Check logs:
```bash
sudo journalctl -u rhearouter -n 50
```

Verify Ollama is running:
```bash
systemctl status ollama
```

### Can't connect via Tailscale

Verify Tailscale is running:
```bash
tailscale status
```

Check firewall rules:
```bash
sudo ufw status
```

Test local access first:
```bash
curl http://localhost:8000/health
```

### Port already in use

Check what's using port 8000:
```bash
sudo lsof -i :8000
```

Kill existing process:
```bash
pkill -f "uvicorn.*rhearouter"
```

## Configuration

Edit `/home/djshanklin/repos/rhearouter/.env` to customize:

- `HOST=0.0.0.0` - Bind to all interfaces (required for Tailscale)
- `PORT=8000` - Change port if needed
- `OLLAMA_BASE_URL=http://localhost:11434` - Ollama backend
- `DEFAULT_TEXT_MODEL=llama3.1:8b` - Default text model
- `DEFAULT_VISION_MODEL=minicpm-v:8b` - Default vision model

After changing configuration:
```bash
sudo systemctl restart rhearouter
```

## Security Notes

- **No authentication by default** - RheaRouter trusts Tailscale network security
- Port 8000 is only accessible from Tailscale network (100.0.0.0/8)
- All data stays on your private network
- No cloud API calls

## Next Steps

1. Test from your MacBook via Tailscale
2. Set up authentication if needed (add API keys to .env)
3. Configure rate limits for your usage
4. Add more models via `ollama pull <model>`
5. Monitor usage via logs: `sudo journalctl -u rhearouter -f`
