# Email Setup Guide - Lead Auto-Response

**Configure email notifications for lead capture system**

---

## 📧 Email Features

When a lead submits the contact form:
1. **Auto-response sent to lead** - Professional immediate response
2. **Notification sent to you** - Know about new leads instantly

---

## ⚙️ Quick Setup (5 minutes)

### Option 1: Gmail (Recommended for Testing)

**Step 1: Create App Password**
1. Go to https://myaccount.google.com/apppasswords
2. Generate app password for "UAPK Gateway"
3. Copy the 16-character password

**Step 2: Configure Environment**

Add to `.env.production`:
```bash
# Email Configuration
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password-here
SMTP_FROM=your-email@gmail.com
ADMIN_EMAIL=your-email@gmail.com
```

**Step 3: Restart Service**
```bash
cd /home/dsanker/uapk-gateway/backend
sudo systemctl restart uapk-gateway
```

**Step 4: Test**
Submit a test lead via the contact form and check your email!

---

### Option 2: SendGrid (Recommended for Production)

**Step 1: Create SendGrid Account**
- Free tier: 100 emails/day
- Sign up: https://sendgrid.com

**Step 2: Create API Key**
- Dashboard → Settings → API Keys
- Create key with "Mail Send" permission
- Copy the API key

**Step 3: Configure Environment**

```bash
# Email Configuration
EMAIL_ENABLED=true
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM=noreply@uapk.info
ADMIN_EMAIL=mail@uapk.info
```

---

### Option 3: AWS SES (For High Volume)

**Step 1: Verify Domain**
- AWS SES Console → Verified identities
- Add and verify uapk.info

**Step 2: Create SMTP Credentials**
- SES Console → SMTP settings
- Create SMTP credentials
- Note the username and password

**Step 3: Configure Environment**

```bash
# Email Configuration
EMAIL_ENABLED=true
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-aws-smtp-username
SMTP_PASSWORD=your-aws-smtp-password
SMTP_FROM=noreply@uapk.info
ADMIN_EMAIL=mail@uapk.info
```

---

## 📧 Email Templates

### Auto-Response to Lead

**Subject:** "We've received your UAPK Gateway inquiry"

**Content:**
- Thank you message
- What happens next (24h response)
- Links to documentation
- Your submission details
- Next steps

**Sender:** noreply@uapk.info (or your configured SMTP_FROM)

### Admin Notification

**Subject:** "🎯 New Lead: [Company] ([Budget])"

**Content:**
- Lead details (name, email, company, role)
- Use case description
- Timeline and budget
- Quick actions:
  - View in Dashboard button
  - Reply to Lead button
- Lead ID for tracking

**Recipient:** Your admin email (ADMIN_EMAIL)

---

## 🧪 Testing

### Test the Email System

**1. Check Configuration:**
```bash
cd /home/dsanker/uapk-gateway/backend
source ../venv/bin/activate
python -c "from app.services.email import get_email_service; svc = get_email_service(); print('Enabled:', svc.enabled, 'From:', svc.smtp_from)"
```

**2. Submit Test Lead:**
```bash
curl -X POST http://localhost:8000/api/v1/leads \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Test User",
    "email": "your-email@example.com",
    "company": "Test Company",
    "use_case": "Testing email automation",
    "timeline": "Immediate",
    "budget": "$15K-$25K"
  }'
```

**3. Check Emails:**
- Lead should receive auto-response at their email
- You should receive notification at ADMIN_EMAIL
- Check spam folder if not received

**4. Check Service Logs:**
```bash
sudo journalctl -u uapk-gateway -n 50 | grep email
```

---

## ⚠️ Troubleshooting

### Emails Not Sending

**Check 1: Is email enabled?**
```bash
grep EMAIL_ENABLED .env
# Should show: EMAIL_ENABLED=true
```

**Check 2: Are SMTP credentials set?**
```bash
grep SMTP_USER .env
grep SMTP_PASSWORD .env
# Should show your credentials
```

**Check 3: Check service logs**
```bash
sudo journalctl -u uapk-gateway -f | grep email
```

Look for:
- `email_sent` - Success!
- `email_not_sent_disabled` - EMAIL_ENABLED=false
- `email_not_sent_no_config` - SMTP credentials missing
- `email_send_failed` - Check SMTP settings

### Gmail Blocks Emails

**Error:** "Username and Password not accepted"

**Fix:**
1. Enable 2-factor authentication on Gmail
2. Create App Password (https://myaccount.google.com/apppasswords)
3. Use app password, not your regular password

### SendGrid "Sender not verified"

**Error:** "Sender identity not verified"

**Fix:**
1. Verify sender email in SendGrid dashboard
2. Or verify your domain
3. Update SMTP_FROM to verified email

---

## 🎯 Production Recommendations

### For Production Use:

**1. Use Professional Email Service**
- ✅ SendGrid, AWS SES, or Mailgun
- ❌ Don't use personal Gmail for business

**2. Verify Your Domain**
- Set up SPF, DKIM, DMARC records
- Prevents emails going to spam
- Professional sender reputation

**3. Monitor Email Delivery**
- Track open rates
- Monitor bounce rates
- Set up alerts for failed sends

**4. Compliance**
- Include unsubscribe link (if sending marketing emails)
- GDPR compliance for EU leads
- CAN-SPAM compliance for US

---

## 📝 Current Status

**Email Service:** ✅ Implemented
**Templates:** ✅ Created (auto-response + admin notification)
**Integration:** ✅ Connected to leads API

**To Activate:**
1. Add SMTP configuration to `.env` or `.env.production`
2. Set `EMAIL_ENABLED=true`
3. Restart service
4. Test with sample lead

**Without Email Configuration:**
- Leads still captured in database
- Visible in admin dashboard
- No emails sent (logged as "email_not_sent_disabled")

---

## ✅ Next Steps

1. **Choose email provider** (Gmail for testing, SendGrid for production)
2. **Configure .env** with SMTP settings
3. **Restart service** to load new config
4. **Test** by submitting contact form
5. **Verify** emails received

**After setup:** Every lead submission will automatically:
- Send professional auto-response to prospect
- Notify you via email with lead details
- Appear in admin dashboard for tracking

---

**Email automation ready to activate!** 🚀
