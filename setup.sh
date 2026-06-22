#!/bin/bash
set -e

echo "=== 音声入力アプリ セットアップ ==="

cd "$(dirname "$0")"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "仮想環境を作成中..."
    python3 -m venv venv
fi

# Activate and install
echo "依存パッケージをインストール中..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "起動方法:"
echo "  source venv/bin/activate && python3 main.py"
echo ""
echo "初回起動後、メニューバーのアイコンから「設定」を開き"
echo "OpenAI APIキーを入力してください。"
echo ""
echo "必要な権限（macOS）:"
echo "  1. マイク: システム設定 > プライバシーとセキュリティ > マイク"
echo "  2. アクセシビリティ: システム設定 > プライバシーとセキュリティ > アクセシビリティ"
echo "     ※ ホットキーとテキスト貼り付け機能に必要です"
