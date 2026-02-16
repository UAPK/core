# GCP Firewall Setup for UAPK Gateway

## Your Server Details

- **External IP**: 34.171.83.82
- **Port**: 8000
- **Service**: UAPK Gateway

---

## 🔥 Open Port 8000 - Step-by-Step Guide

### Method 1: GCP Console (Recommended - Easy)

**Time**: 2 minutes

**Steps**:

1. **Go to GCP Firewall Page**:
   
   https://console.cloud.google.com/net-security/firewall-manager/firewall-policies/list
   
   Or navigate: Navigation Menu → VPC Network → Firewall

2. **Click "CREATE FIREWALL RULE"**

3. **Configure the rule**:
   
   ```
   Name:                  allow-uapk-gateway
   Description:           Allow UAPK Gateway external access on port 8000
   Network:               default (or your network)
   Priority:              1000
   Direction of traffic:  Ingress
   Action on match:       Allow
   Targets:               All instances in the network
   Source filter:         IPv4 ranges
   Source IPv4 ranges:    0.0.0.0/0
   Protocols and ports:   Specified protocols and ports
     ☑ TCP: 8000
   ```

4. **Click "CREATE"**

5. **Wait 30 seconds** for the rule to propagate

6. **Test external access**:
   ```bash
   curl http://34.171.83.82:8000/healthz
   # Should return: {"status":"ok"}
   ```

---

### Method 2: gcloud Command (For Scripts)

If you have gcloud configured with proper authentication:

```bash
gcloud compute firewall-rules create allow-uapk-gateway \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow UAPK Gateway external access" \
  --direction INGRESS \
  --priority 1000
```

**Test**:
```bash
gcloud compute firewall-rules describe allow-uapk-gateway
```

---

### Method 3: More Secure (Restricted Access)

Instead of allowing everyone (0.0.0.0/0), allow only specific IPs:

**Your office IP**:
```
Source IPv4 ranges: YOUR_IP/32
```

**Multiple IPs**:
```
Source IPv4 ranges: 203.0.113.1/32, 198.51.100.1/32
```

**Your office network**:
```
Source IPv4 ranges: 203.0.113.0/24
```

**How to find your IP**:
```bash
curl ifconfig.me
```

---

## 🧪 Verification Steps

After creating the firewall rule:

### 1. Wait for Propagation (30-60 seconds)
```bash
sleep 30
```

### 2. Test External Health Check
```bash
curl http://34.171.83.82:8000/healthz
# Expected: {"status":"ok"}
```

### 3. Test API Documentation
```
Open in browser: http://34.171.83.82:8000/docs
# Should show interactive API documentation
```

### 4. Test from Different Network
Use your phone (disconnected from WiFi) or ask someone else to test:
```
curl http://34.171.83.82:8000/healthz
```

---

## 🔒 Security Considerations

### Current Setup: Open to World (0.0.0.0/0)

**Pros**:
- ✅ Anyone can access (good for testing)
- ✅ Customers can connect from anywhere
- ✅ Easy to demo

**Cons**:
- ⚠️ Exposed to internet (bot scans, attacks)
- ⚠️ DDoS risk
- ⚠️ Brute force attempts

**Mitigations Already in Place**:
- ✅ Rate limiting (60-200 req/min)
- ✅ Authentication required (API keys, JWT)
- ✅ SSRF protection
- ✅ Request size limits
- ✅ No default credentials

### Recommended: Add CloudFlare (Free)

1. Sign up: https://www.cloudflare.com
2. Add your domain
3. Point domain to: 34.171.83.82
4. Enable Cloudflare proxy
5. Get:
   - ✅ DDoS protection (free)
   - ✅ SSL/TLS (free)
   - ✅ CDN (free)
   - ✅ Firewall rules (free)
   - ✅ Rate limiting (enhanced)

---

## 🎯 Production Security Checklist

Once firewall is open:

- [ ] Add domain name (yourdomain.com)
- [ ] Set up SSL/TLS certificate (Let's Encrypt or Cloudflare)
- [ ] Configure CORS_ORIGINS in .env.production
- [ ] Set up monitoring (UptimeRobot free tier)
- [ ] Configure backups (pg_dump cron job)
- [ ] Set up log rotation
- [ ] Consider CloudFlare for DDoS protection
- [ ] Test from external network
- [ ] Update GATEWAY_ALLOWED_WEBHOOK_DOMAINS as needed

---

## 📊 After Firewall Opens

Your UAPK Gateway will be accessible at:

**Without domain**:
- http://34.171.83.82:8000
- http://34.171.83.82:8000/docs

**With domain** (after DNS setup):
- http://yourdomain.com:8000
- http://yourdomain.com:8000/docs

**With SSL** (after Cloudflare/Caddy):
- https://yourdomain.com
- https://yourdomain.com/docs

---

## 🚨 Troubleshooting

### Firewall rule created but can't access?

1. **Wait 60 seconds** (rule propagation)

2. **Check rule exists**:
   ```bash
   gcloud compute firewall-rules list | grep 8000
   ```

3. **Check server is listening**:
   ```bash
   lsof -i :8000
   # Should show uvicorn process
   ```

4. **Check from inside VM**:
   ```bash
   curl http://localhost:8000/healthz
   # Should work
   ```

5. **Check from external**:
   ```bash
   curl http://34.171.83.82:8000/healthz
   # Should work after firewall opens
   ```

### Still blocked?

- Check if VM has network tag restrictions
- Check if VPC has custom routes blocking traffic
- Verify the rule targets "All instances"
- Check GCP project quotas/limits

---

## ✅ Quick Test

After creating firewall rule, run this:

```bash
# Wait for propagation
sleep 30

# Test external access
curl http://34.171.83.82:8000/healthz

# If successful, you'll see:
# {"status":"ok"}
```

---

**Once firewall is open, your UAPK Gateway is accessible worldwide! 🌍**

