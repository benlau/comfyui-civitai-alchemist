#!/bin/bash
set -e

echo "=== ComfyUI Civitai Alchemist 開發環境設置 ==="
echo ""

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. 檢查必要工具
echo -e "${YELLOW}[1/10] 檢查必要工具...${NC}"
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}錯誤: 需要 Python 3.10+${NC}"; exit 1; }
command -v uv >/dev/null 2>&1 || { echo -e "${RED}錯誤: 需要 uv package manager${NC}"; exit 1; }
command -v git >/dev/null 2>&1 || { echo -e "${RED}錯誤: 需要 git${NC}"; exit 1; }
command -v nvidia-smi >/dev/null 2>&1 || { echo -e "${RED}錯誤: nvidia-smi 不可用,請確認 GPU driver 已安裝${NC}"; exit 1; }
echo -e "${GREEN}✓ 工具檢查完成${NC}"

# 2. 驗證 GPU (RTX 5090)
echo -e "${YELLOW}[2/10] 驗證 GPU 環境...${NC}"
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
if [[ $GPU_NAME == *"5090"* ]]; then
    echo -e "${GREEN}✓ 檢測到 GPU: $GPU_NAME${NC}"
else
    echo -e "${YELLOW}! 警告: 檢測到的 GPU 不是 RTX 5090: $GPU_NAME${NC}"
    echo -e "${YELLOW}  性能優化可能不完全適用${NC}"
fi

# 3. 建立虛擬環境
echo -e "${YELLOW}[3/10] 建立虛擬環境...${NC}"
if [ ! -d ".venv" ]; then
    uv venv .venv --python 3.12
    echo -e "${GREEN}✓ 虛擬環境建立完成${NC}"
else
    echo -e "${GREEN}✓ 虛擬環境已存在${NC}"
fi

# 4. 啟動虛擬環境
echo -e "${YELLOW}[4/10] 啟動虛擬環境...${NC}"
source .venv/bin/activate
echo -e "${GREEN}✓ 虛擬環境已啟動${NC}"

# 5. 安裝 PyTorch with CUDA 12.8 及所有依賴
echo -e "${YELLOW}[5/10] 安裝 PyTorch 2.7+ 及依賴 (這可能需要幾分鐘)...${NC}"
echo -e "${BLUE}使用 CUDA 12.8 索引安裝 PyTorch...${NC}"
UV_TORCH_BACKEND=cu128 uv pip install -e .
echo -e "${GREEN}✓ PyTorch 及核心依賴安裝完成${NC}"

# 6. 詢問是否安裝 Flash Attention
echo -e "${YELLOW}[6/10] Flash Attention 安裝選項...${NC}"
echo -e "${BLUE}Flash Attention 可以提供額外加速,但在 RTX 5090 上可能有相容性問題${NC}"
echo -e "${BLUE}SageAttention 已安裝且更穩定,建議先測試後再決定是否需要 Flash Attention${NC}"
read -p "是否安裝 Flash Attention? (y/N): " install_flash
if [[ $install_flash =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}嘗試安裝 Flash Attention...${NC}"
    if uv pip install flash-attn --no-build-isolation 2>/dev/null; then
        echo -e "${GREEN}✓ Flash Attention 安裝成功${NC}"
    else
        echo -e "${YELLOW}! Flash Attention 安裝失敗 (這是正常的)${NC}"
        echo -e "${YELLOW}  將使用 SageAttention 作為加速方案${NC}"
    fi
else
    echo -e "${GREEN}✓ 跳過 Flash Attention,將使用 SageAttention${NC}"
fi

# 7. Clone ComfyUI 本體
echo -e "${YELLOW}[7/10] 下載 ComfyUI 本體...${NC}"
COMFYUI_DIR="../ComfyUI"
if [ ! -d "$COMFYUI_DIR" ]; then
    cd ..
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd comfyui-civitai-alchemist
    echo -e "${GREEN}✓ ComfyUI 下載完成${NC}"
else
    echo -e "${GREEN}✓ ComfyUI 已存在${NC}"
fi

# 8. 建立 symlink: ComfyUI 使用我們的虛擬環境
echo -e "${YELLOW}[8/10] 設置 ComfyUI 虛擬環境連結...${NC}"
if [ -L "$COMFYUI_DIR/.venv" ]; then
    rm "$COMFYUI_DIR/.venv"
fi
if [ -e "$COMFYUI_DIR/.venv" ] && [ ! -L "$COMFYUI_DIR/.venv" ]; then
    echo -e "${YELLOW}! ComfyUI 已有實體虛擬環境,重新命名為 .venv.backup${NC}"
    mv "$COMFYUI_DIR/.venv" "$COMFYUI_DIR/.venv.backup"
fi
ln -s "$(pwd)/.venv" "$COMFYUI_DIR/.venv"
echo -e "${GREEN}✓ 虛擬環境連結完成${NC}"

# 9. 建立 custom_nodes 目錄並連結
echo -e "${YELLOW}[9/10] 設置 custom node 連結...${NC}"
mkdir -p "$COMFYUI_DIR/custom_nodes"
bash scripts/link.sh
echo -e "${GREEN}✓ Custom node 連結完成${NC}"

# 10. 驗證安裝
echo -e "${YELLOW}[10/10] 驗證安裝...${NC}"
bash scripts/check_env.sh

echo ""
echo -e "${GREEN}=== 設置完成! ===${NC}"
echo ""
echo -e "${BLUE}下一步:${NC}"
echo "  1. 啟動 ComfyUI: ${YELLOW}bash scripts/run_comfyui.sh${NC}"
echo "  2. 從 Windows 瀏覽器開啟: ${YELLOW}http://localhost:8188${NC}"
echo "  3. 開發時修改 nodes/ 目錄下的檔案"
echo "  4. 重啟 ComfyUI 看到變更"
echo "  5. (可選) 執行性能測試: ${YELLOW}bash scripts/benchmark.sh${NC}"
echo ""
echo -e "${BLUE}環境變數已在 .env 檔案中配置,run_comfyui.sh 會自動載入${NC}"
echo ""
