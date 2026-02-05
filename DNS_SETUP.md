# RheaRouter DNS and Access Setup

## ✅ Current Setup - Much Better!

Your RheaRouter is now accessible via a stable DNS name with HTTPS:

### Primary Access (HTTPS, recommended)
```
https://dsthink.tail813f4e.ts.net
```

✅ **Benefits:**
- Stable DNS name (doesn't change)
- Automatic HTTPS/TLS encryption
- Works from any Tailscale device
- MagicDNS enabled

### Alternative Access Methods

**1. Tailscale MagicDNS (short name)**
```
http://dsthink:8000
```
Works if MagicDNS is enabled on your devices

**2. Full Tailscale DNS**
```
http://dsthink.tail813f4e.ts.net:8000
```
Bypass Tailscale Serve proxy, direct to port 8000

**3. Tailscale IP (not recommended)**
```
http://100.87.176.89:8000
```
Less durable, IP could change

## Testing Your Endpoints

```bash
# HTTPS endpoint (recommended)
curl https://dsthink.tail813f4e.ts.net/health

# Get available models
curl https://dsthink.tail813f4e.ts.net/v1/models

# Chat completion
curl -X POST https://dsthink.tail813f4e.ts.net/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "llama3.1:8b"
  }'
```

## Using with OpenAI-Compatible Clients

### Python
```python
import openai

client = openai.OpenAI(
    base_url="https://dsthink.tail813f4e.ts.net/v1",
    api_key="not-needed"  # Unless you enabled auth
)

response = client.chat.completions.create(
    model="llama3.1:8b",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### curl (OpenAI-compatible)
```bash
curl -X POST https://dsthink.tail813f4e.ts.net/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Write a haiku about AI"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

## Setting Up Custom Subdomain (Optional)

If you want something like `rhearouter.tail813f4e.ts.net`:

### Option 1: Tailscale Custom Hostname

Check your Tailscale admin console:
1. Go to https://login.tailscale.com/admin/machines
2. Find your machine (dsthink)
3. Click "..." → "Edit hostname"
4. Change to something like "rhearouter"

Then your URLs become:
- `https://rhearouter.tail813f4e.ts.net`

### Option 2: Custom Domain (Advanced)

If you own a domain, you can use Tailscale's custom domain feature:
1. Go to Tailscale admin console
2. DNS → Custom domains
3. Add your domain
4. Set up DNS records

Then you get:
- `https://api.yourdomain.com`

## Tailscale Serve Management

### Check current status
```bash
tailscale serve status
```

### Disable proxy
```bash
tailscale serve --https=443 off
```

### Re-enable proxy
```bash
tailscale serve --bg http://127.0.0.1:8000
```

### Serve on custom port
```bash
tailscale serve --bg --set-path=/api http://127.0.0.1:8000
```

## MagicDNS Configuration

Ensure MagicDNS is enabled on all your devices:

### On Linux (this machine)
```bash
tailscale status | grep "MagicDNS"
```

### On macOS/Windows
Check Tailscale preferences → Enable MagicDNS

### Test MagicDNS
```bash
# From any Tailscale device:
ping dsthink
# Should resolve to 100.87.176.89
```

## Recommended Configuration

### For Development
Use direct port access for faster iteration:
```
http://dsthink:8000
```

### For Production/Sharing
Use HTTPS via Tailscale Serve:
```
https://dsthink.tail813f4e.ts.net
```
- Encrypted traffic
- No port numbers needed
- Professional appearance

## Adding to Client Libraries

### Environment Variable
```bash
export OPENAI_BASE_URL="https://dsthink.tail813f4e.ts.net/v1"
export OPENAI_API_KEY="not-needed"
```

### Configuration File (~/.config/openai/config)
```ini
[default]
api_base = https://dsthink.tail813f4e.ts.net/v1
api_key = not-needed
```

### VS Code Extension (Continue, etc.)
```json
{
  "models": [{
    "title": "RheaRouter",
    "provider": "openai",
    "model": "llama3.1:8b",
    "apiBase": "https://dsthink.tail813f4e.ts.net/v1"
  }]
}
```

## Troubleshooting

### Can't resolve dsthink.tail813f4e.ts.net

**Check MagicDNS:**
```bash
tailscale status
# Should show MagicDNS: true
```

**Enable if needed:**
```bash
tailscale up --accept-dns=true
```

### HTTPS certificate errors

Tailscale automatically provisions TLS certificates. If you see errors:
1. Ensure you're accessing via the full DNS name
2. Check Tailscale is running: `tailscale status`
3. Try restarting serve: `tailscale serve reset && tailscale serve --bg http://127.0.0.1:8000`

### Port 8000 conflicts

If another service uses port 8000:

**Change RheaRouter port:**
Edit `/home/djshanklin/repos/rhearouter/.env`:
```bash
PORT=8001
```

Then update Tailscale serve:
```bash
sudo systemctl restart rhearouter
tailscale serve --bg http://127.0.0.1:8001
```

### Tailscale serve not persisting after reboot

Tailscale serve configuration is persistent, but verify with:
```bash
tailscale serve status
```

If it's off after reboot:
```bash
tailscale serve --bg http://127.0.0.1:8000
```

Add to startup script if needed.

## Monitoring

### Check DNS resolution
```bash
# From any Tailscale device
nslookup dsthink.tail813f4e.ts.net
dig dsthink.tail813f4e.ts.net
```

### Check HTTPS certificate
```bash
curl -v https://dsthink.tail813f4e.ts.net/health 2>&1 | grep "subject:"
```

### Monitor access logs
```bash
sudo journalctl -u rhearouter -f
```

## Summary

**Your stable endpoints:**

| Purpose | URL | Notes |
|---------|-----|-------|
| **Primary (HTTPS)** | `https://dsthink.tail813f4e.ts.net` | ✅ Recommended |
| Development | `http://dsthink:8000` | Quick, MagicDNS |
| Direct access | `http://dsthink.tail813f4e.ts.net:8000` | Bypasses proxy |
| IP fallback | `http://100.87.176.89:8000` | ❌ Not durable |

**Use the HTTPS endpoint for:**
- Client library configuration
- Sharing with teammates
- Production usage
- Mobile apps

**Use the direct port for:**
- Local development
- Testing
- Debugging
