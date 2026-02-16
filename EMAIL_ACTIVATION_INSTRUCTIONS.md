# 📧 Email Activation Instructions

**Email system is configured and ready - just needs activation**

---

## ✅ Current Status

- ✅ Email service code implemented
- ✅ Email templates created (auto-response + admin notification)
- ✅ Configuration added to .env.production
- ✅ Integrated with leads API
- ⚠️ **EMAIL_ENABLED=false** (not sending emails yet)

**Leads are being captured**, but emails are not sent until you enable them.

---

## 🚀 Quick Activation (5 Minutes)

### **Option 1: Gmail (Fastest)**

**Step 1: Create Gmail App Password**
1. Go to: https://myaccount.google.com/apppasswords
2. Sign in to your Gmail account
3. Click "Create app password"
4. Name it: "UAPK Gateway"
5. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

**Step 2: Update Configuration**

Edit `/home/dsanker/uapk-gateway/.env.production`:

```bash
# Change these lines:
EMAIL_ENABLED=true                    # Change from false to true
SMTP_USER=your-actual-email@gmail.com # Your Gmail address
SMTP_PASSWORD=abcd efgh ijkl mnop     # Your app password (remove spaces)
```

**Step 3: Copy to Backend and Restart**
```bash
cp /home/dsanker/uapk-gateway/.env.production /home/dsanker/uapk-gateway/backend/.env
sudo systemctl restart uapk-gateway
```

**Step 4: Test**
```bash
# Submit test lead
curl -X POST 'http://34.171.83.82:8000/api/v1/leads' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Test",
    "email": "your-email@gmail.com",
    "company": "Test",
    "use_case": "Testing emails"
  }'

# Check your inbox - you should receive:
# 1. Auto-response (to your-email@gmail.com)
# 2. Admin notification (to mail@uapk.info)
```

---

### **Option 2: SendGrid (Better for Production)**

**Step 1: Create SendGrid Account**
1. Sign up: https://sendgrid.com (free tier: 100 emails/day)
2. Verify your email address
3. Create API key:
   - Settings → API Keys → Create API Key
   - Name: "UAPK Gateway"
   - Permissions: "Mail Send" (Full Access)
   - Copy the API key

**Step 2: Update Configuration**

Edit `/home/dsanker/uapk-gateway/.env.production`:

```bash
EMAIL_ENABLED=true
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your-sendgrid-api-key-here
SMTP_FROM=noreply@uapk.info
ADMIN_EMAIL=mail@uapk.info
```

**Step 3: Verify Sender (Important!)**

SendGrid requires sender verification:
1. SendGrid Dashboard → Settings → Sender Authentication
2. Verify single sender: noreply@uapk.info
   OR
3. Verify domain: uapk.info (better for production)

**Step 4: Restart and Test**
```bash
cp /home/dsanker/uapk-gateway/.env.production /home/dsanker/uapk-gateway/backend/.env
sudo systemctl restart uapk-gateway

# Test with curl (same as above)
```

---

## 📧 What Happens When Enabled

### **When Lead Submits Form:**

**1. Lead Receives Auto-Response** (Instant)
```
To: lead@their-company.com
Subject: "We've received your UAPK Gateway inquiry"

Thank you for your interest!

We'll review your inquiry within 24 hours and get back to you.

Your submission:
- Company: [Their Company]
- Use Case: [Their use case]
- Timeline: [Their timeline]
- Budget: [Their budget]

Meanwhile:
- Read our docs: https://uapk.info/docs
- Try open source: https://github.com/UAPK/gateway
- Learn about pilots: https://uapk.info/docs/business/pilot
```

**2. You Receive Notification** (Instant)
```
To: mail@uapk.info
Subject: "🎯 New Lead: [Company] ($20K)"

New Lead Submitted!

Name: John Doe
Email: john@company.com
Company: Acme Corp
Use Case: Settlement agent for IP litigation
Timeline: Immediate
Budget: $15K-$25K

[View in Dashboard] [Reply to Lead]
```

---

## 🧪 Testing

### **Verify Email is Working:**

**1. Check Configuration**
```bash
cd /home/dsanker/uapk-gateway/backend
source ../venv/bin/activate
python -c "from app.services.email import get_email_service; svc = get_email_service(); print('Email Enabled:', svc.enabled); print('From:', svc.smtp_from); print('Admin:', svc.admin_email)"
```

Expected output:
```
Email Enabled: True
From: noreply@uapk.info
Admin: mail@uapk.info
```

**2. Submit Test Lead**
```bash
curl -X POST 'http://34.171.83.82:8000/api/v1/leads' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Your Name",
    "email": "your-email@gmail.com",
    "company": "Test Company",
    "use_case": "Testing the email system",
    "timeline": "Immediate",
    "budget": "$20K"
  }'
```

**3. Check Both Inboxes**
- Lead email (your-email@gmail.com): Should receive auto-response
- Admin email (mail@uapk.info): Should receive notification

**4. Check Service Logs**
```bash
sudo journalctl -u uapk-gateway -n 50 | grep email
```

Look for:
- ✅ `email_sent` - Success!
- ⚠️ `email_not_sent_disabled` - EMAIL_ENABLED=false
- ❌ `email_send_failed` - Check credentials

---

## ⚙️ Current Configuration

**Location:** `/home/dsanker/uapk-gateway/.env.production`

**Current Settings:**
```bash
EMAIL_ENABLED=false          # ← Change to true to activate
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com      # ← Add your email
SMTP_PASSWORD=your-app-password-here # ← Add your app password
SMTP_FROM=noreply@uapk.info
ADMIN_EMAIL=mail@uapk.info   # ← Configured!
```

**To Activate:**
1. Get Gmail app password (or SendGrid API key)
2. Update SMTP_USER and SMTP_PASSWORD
3. Change EMAIL_ENABLED to `true`
4. Copy to backend: `cp .env.production backend/.env`
5. Restart: `sudo systemctl restart uapk-gateway`

---

## 🎯 What You Get

**When Email is Enabled:**

✅ **Instant response** to every lead
✅ **Professional impression** (not manual email)
✅ **Never miss a lead** (notifications to your inbox)
✅ **Automated nurturing** (lead gets helpful info)
✅ **Time savings** (no manual follow-ups)

**Lead Experience:**
```
Submit form → Instant email → "They're on it!" → Trust built
```

**Your Experience:**
```
New lead → Email notification → Review in dashboard → Contact
```

---

## 📝 Summary

**Status:** ✅ Email system configured and ready
**Current:** Emails disabled (EMAIL_ENABLED=false)
**Leads:** Still captured in database and dashboard
**To Activate:** Follow Option 1 or Option 2 above (5 minutes)

**When you're ready to activate:**
1. Get SMTP credentials (Gmail app password or SendGrid API key)
2. Update .env.production
3. Restart service
4. Test with a lead submission

---

**Email system is ready to go live whenever you want!**

For now, leads will appear in your admin dashboard at:
http://34.171.83.82:8000/admin → Leads tab

When you enable email, you'll also get instant notifications in your inbox! 📬