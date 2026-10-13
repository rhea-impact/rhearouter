# RheaRouter Quick Reference

## 🌐 Your Stable Endpoint

```
https://dsthink.tail0ffb4a.ts.net
```

✅ **This is your durable, HTTPS-enabled endpoint**
- Works from any Tailscale device
- Automatic TLS encryption
- Won't change

## 🚀 Quick Commands

### Test Health
```bash
curl https://dsthink.tail0ffb4a.ts.net/health
```

### List Models
```bash
curl https://dsthink.tail0ffb4a.ts.net/v1/models
```

### Chat Completion
```bash
curl -X POST https://dsthink.tail0ffb4a.ts.net/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

## 🔧 Service Management

```bash
# Check status
sudo systemctl status rhearouter

# Restart
sudo systemctl restart rhearouter

# View logs
sudo journalctl -u rhearouter -f

# Check Tailscale serve
tailscale serve status
```

## 🔌 Use with OpenAI Libraries

```python
import openai

client = openai.OpenAI(
    base_url="https://dsthink.tail0ffb4a.ts.net/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="llama3.1:8b",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## 📚 Documentation

- `DNS_SETUP.md` - Full DNS configuration guide
- `SECURITY_SETUP.md` - Security configuration
- `TAILSCALE_SETUP.md` - Tailscale setup details
- `API.md` - Complete API reference
- `QUICKSTART.md` - Quick start guide

## 🎯 Available Models

- `llama3.1:8b` - Fast general text
- `minicpm-v:8b` - Vision/OCR
- `deepseek-r1:8b` - Reasoning/logic

## 🛠️ Configuration Files

- `/home/djshanklin/repos/rhearouter/.env` - Environment config
- `/etc/systemd/system/rhearouter.service` - Service definition
- `~/.config/tailscale/` - Tailscale config
