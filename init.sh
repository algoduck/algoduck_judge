#!/bin/bash

echo "🚀 EC2 초기 설정 시작..."

# 1. 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 2. Docker 설치
echo "🐳 Docker 설치 중..."
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 3. Git 설치
echo "🔧 Git 설치 중..."
sudo apt install -y git

# 4. UFW 방화벽 비활성화 (테스트 목적)
sudo ufw disable

# 5. Docker 적용을 위해 SSH 재접속 필요
echo "⚠️ Docker 그룹 적용을 위해 SSH 재접속이 필요합니다."
echo "✅ 초기 설정 완료!"