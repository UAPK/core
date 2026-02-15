#!/bin/bash
# OPTION 1: Docker Deployment (Recommended)

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     OPTION 1: Docker Production Deployment                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found. Installing Docker..."
    echo ""
    read -p "Install Docker now? (yes/no): " install_docker
    
    if [ "$install_docker" = "yes" ]; then
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sudo sh /tmp/get-docker.sh
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        
        echo ""
        echo "✅ Docker installed!"
        echo "⚠️  Please log out and back in for group membership to take effect"
        echo "   Then run this script again."
        exit 0
    else
        echo "❌ Docker is required for this deployment option."
        exit 1
    fi
fi

echo "✅ Docker available: $(docker --version)"
echo ""

# Rest of deployment
./deploy-to-production.sh
