#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}啟動 ComfyUI...${NC}"

# 載入環境變數
if [ -f ".env" ]; then
    source .env
    echo -e "${GREEN}✓ 已載入 .env 環境變數${NC}"
fi

# 切換到 ComfyUI 目錄
cd ../ComfyUI

# 啟動虛擬環境
source .venv/bin/activate

# 顯示資訊
echo -e "${BLUE}ComfyUI 將啟動在:${NC}"
echo -e "  本機: ${GREEN}http://127.0.0.1:8188${NC}"
echo -e "  Windows: ${GREEN}http://localhost:8188${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止${NC}"
echo ""

# 啟動 ComfyUI (WSL2 使用 --listen 0.0.0.0 允許 Windows 存取)
python main.py --listen 0.0.0.0

# 返回原目錄
cd - > /dev/null
