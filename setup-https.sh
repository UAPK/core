#!/bin/bash
# Quick HTTPS setup using Caddy reverse proxy

echo "Setting up HTTPS for UAPK Gateway..."

# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy

# Create Caddyfile
cat > /tmp/Caddyfile << 'EOF'
# Serve on IP address with self-signed cert for now
https://34.171.83.82:443 {
    reverse_proxy localhost:8000
    tls internal
}

# Also serve on HTTP for backward compatibility
http://34.171.83.82:80 {
    reverse_proxy localhost:8000
}
EOF

sudo mv /tmp/Caddyfile /etc/caddy/Caddyfile

# Restart Caddy
sudo systemctl restart caddy
sudo systemctl enable caddy

echo "✅ HTTPS setup complete!"
echo "API now available at:"
echo "  - https://34.171.83.82:443 (HTTPS with self-signed cert)"
echo "  - http://34.171.83.82:8000 (original HTTP)"
