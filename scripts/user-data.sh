#!/bin/bash
# EC2 "User data" script for the Launch Template (Amazon Linux 2023).
# Every instance the Auto Scaling Group launches runs this once at first boot,
# so new instances come up with the app already deployed.
#
# >>> THE REPO URL BELOW my own GitHub repository <<<
REPO_URL="https://github.com/Urwa2345/devops-lab.git"

set -xe
exec > /var/log/user-data.log 2>&1

dnf update -y
dnf install -y docker git

systemctl enable --now docker
usermod -aG docker ec2-user

# Docker Compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
     -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Deploy the application
git clone "$REPO_URL" /opt/devops-lab
cd /opt/devops-lab
docker compose up -d --build
