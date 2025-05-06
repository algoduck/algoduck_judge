#!/bin/bash

echo "🔧 Running hook installation..."

# Step 1: pre-commit 설치 확인 및 설치
if ! command -v pre-commit &> /dev/null
then
  echo "📦 pre-commit이 설치되어 있지 않습니다. 설치를 진행합니다..."
  pip install pre-commit
else
  echo "✅ pre-commit이 이미 설치되어 있습니다."
fi

# Step 2: pre-commit hook 등록
echo "🔗 pre-commit hook을 Git에 등록합니다..."
pre-commit install
echo "✅ pre-commit hook 설치 완료"

# Step 3: prepare-commit-msg hook 복사
HOOK_PATH=".git/hooks/prepare-commit-msg"
SOURCE_HOOK="hooks/prepare-commit-msg"

echo "🪝 prepare-commit-msg hook 설치 중..."

if [ -d ".git/hooks" ]; then
  cp "$SOURCE_HOOK" "$HOOK_PATH"
  chmod +x "$HOOK_PATH"
  echo "✅ Git hook 설치 완료: $HOOK_PATH"
else
  echo "❌ .git/hooks 디렉토리가 없습니다. 프로젝트 루트에서 실행했는지 확인해주세요."
fi
