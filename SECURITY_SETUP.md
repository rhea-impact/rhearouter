# RheaRouter Security Setup

## Current Security Status

✅ **Already Protected:**
- Only accessible via Tailscale private network (100.0.0.0/8)
- Not exposed to public internet
- Running as non-root user (djshanklin)
- Systemd service isolation enabled

## Security Layers

### 1. Network-Level Protection (Active)

Your Tailscale network provides the primary security layer. Port 8000 is only accessible from:
- Your Tailscale-connected devices
- Not accessible from public internet
- Not accessible from local network (unless you expose it)

**Verify network isolation:**
```bash
# Check firewall rules
sudo ufw status

# Should NOT see port 8000 open to 0.0.0.0/0
```

### 2. API Key Authentication (Recommended)

Add API key authentication for additional security:

**Step 1: Generate API keys**
```bash
cd /home/djshanklin/repos/rhearouter

# Generate secure API keys
python3 << 'EOF'
import secrets
print("# Add these to your .env file:")
for i in range(3):
    key = secrets.token_urlsafe(32)
    print(f"API_KEY_{i+1}={key}")
EOF
```

**Step 2: Add to .env**
```bash
# Edit .env and add:
API_KEYS=key1,key2,key3  # Replace with generated keys
FEATURE_AUTH=true
```

**Step 3: Restart service**
```bash
sudo systemctl restart rhearouter
```

**Step 4: Use API keys in requests**
```bash
curl -X POST http://100.87.176.89:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

### 3. Firewall Configuration

Restrict access to Tailscale network only:

```bash
# Allow only from Tailscale network (100.0.0.0/8)
sudo ufw allow from 100.0.0.0/8 to any port 8000 comment 'RheaRouter Tailscale'

# Deny from everywhere else
sudo ufw deny 8000

# Check rules
sudo ufw status numbered
```

### 4. Rate Limiting (Active)

Built-in rate limiting protects against abuse:

**Current limits (in .env):**
```bash
GLOBAL_RATE_LIMIT=60          # 60 requests/minute globally
PER_CLIENT_RATE_LIMIT=20      # 20 requests/minute per client
RATE_LIMIT_BURST=10           # Burst allowance
```

**Adjust for your needs:**
- Lower limits for stricter control
- Higher limits if you have multiple users

### 5. HTTPS/TLS (Optional)

For additional encryption, set up a reverse proxy with TLS:

**Option A: Tailscale HTTPS**
```bash
# Tailscale provides automatic HTTPS
tailscale serve https / http://127.0.0.1:8000

# Access via: https://dsthink.tail-scale.ts.net
```

**Option B: Nginx Reverse Proxy**
```nginx
# /etc/nginx/sites-available/rhearouter
server {
    listen 443 ssl;
    server_name dsthink.tail-scale.ts.net;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 6. Request Logging & Monitoring

Monitor for suspicious activity:

**View live requests:**
```bash
sudo journalctl -u rhearouter -f
```

**Check for errors:**
```bash
sudo journalctl -u rhearouter -p err -n 50
```

**Monitor rate limit hits:**
```bash
sudo journalctl -u rhearouter | grep "429"
```

### 7. Input Validation (Built-in)

RheaRouter validates all inputs:
- Model names validated against available models
- Image sizes limited (10MB default)
- Token limits enforced
- Malformed requests rejected

### 8. Audit Trail

All requests are logged with:
- Request ID (UUID)
- Client IP
- Model used
- Timestamp
- Duration
- Success/failure

**Query SQLite logs (when persistence is enabled):**
```bash
sqlite3 /var/lib/rhearouter/requests.db "
  SELECT timestamp, model_requested, client_ip, error_type
  FROM requests
  WHERE timestamp >= datetime('now', '-1 hour')
  ORDER BY timestamp DESC;
"
```

## Recommended Security Configuration

**For personal use on Tailscale:**

```bash
# .env configuration
FEATURE_AUTH=false              # Optional: false if only you use it
GLOBAL_RATE_LIMIT=60           # Reasonable default
PER_CLIENT_RATE_LIMIT=20       # Prevents abuse
```

**For shared use (2-5 users):**

```bash
# .env configuration
FEATURE_AUTH=true               # Enable API keys
API_KEYS=key1,key2,key3        # One per user
GLOBAL_RATE_LIMIT=100          # Higher global limit
PER_CLIENT_RATE_LIMIT=30       # Per-user limit
```

## Security Checklist

- [ ] Verify only accessible via Tailscale (test from outside)
- [ ] Generate and configure API keys (if sharing)
- [ ] Configure firewall rules (UFW)
- [ ] Set appropriate rate limits
- [ ] Enable request logging
- [ ] Review logs periodically
- [ ] Keep system updated (`sudo apt update && sudo apt upgrade`)
- [ ] Keep Ollama updated (`ollama pull <model>`)

## Testing Security

**Test 1: Verify public internet cannot access**
From a non-Tailscale device:
```bash
curl http://YOUR_PUBLIC_IP:8000/health
# Should timeout or be refused
```

**Test 2: Verify Tailscale access works**
From your MacBook (on Tailscale):
```bash
curl http://100.87.176.89:8000/health
# Should return {"status":"healthy",...}
```

**Test 3: Verify rate limiting**
```bash
# Send 25 requests quickly
for i in {1..25}; do
  curl http://100.87.176.89:8000/health &
done
wait

# Should see some 429 responses
```

**Test 4: Verify API key (if enabled)**
```bash
# Without key (should fail)
curl http://100.87.176.89:8000/v1/chat/completions

# With key (should work)
curl -H "Authorization: Bearer YOUR_KEY" \
  http://100.87.176.89:8000/v1/chat/completions
```

## Threat Model

**Protected Against:**
- ✅ Public internet access
- ✅ Brute force attacks (rate limiting)
- ✅ Unauthorized access (API keys optional)
- ✅ Malformed requests (input validation)
- ✅ Resource exhaustion (VRAM flow valve, rate limits)

**Not Protected Against (by design):**
- ❌ Trusted Tailscale users (you control who's on your network)
- ❌ Malicious prompts (content filtering not included)
- ❌ Physical access to the machine

**Acceptable Because:**
- Tailscale provides device authentication
- You control who joins your Tailscale network
- Local inference = full control over data
- No cloud providers = no data leakage risk

## Emergency Procedures

**If suspicious activity detected:**

1. **Stop the service immediately:**
```bash
sudo systemctl stop rhearouter
```

2. **Review logs:**
```bash
sudo journalctl -u rhearouter -n 1000 > /tmp/rhearouter-audit.log
grep "429\|401\|403\|500" /tmp/rhearouter-audit.log
```

3. **Check active connections:**
```bash
sudo lsof -i :8000
```

4. **Rotate API keys (if using):**
Generate new keys and update .env

5. **Check Tailscale access:**
```bash
tailscale status
# Review who has access to your network
```

## Additional Hardening (Optional)

For paranoid-level security:

1. **Enable AppArmor/SELinux profile**
2. **Use dedicated service user (not djshanklin)**
3. **Chroot the service**
4. **Enable audit logging (auditd)**
5. **Set up intrusion detection (fail2ban)**
6. **Encrypt SQLite database (if storing sensitive data)**

## Support

Security concerns? Check:
1. Logs: `sudo journalctl -u rhearouter -f`
2. Firewall: `sudo ufw status verbose`
3. Tailscale: `tailscale status`
4. Process: `ps aux | grep uvicorn`
