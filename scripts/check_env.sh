#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=== 環境檢查 ==="
echo ""

EXIT_CODE=0

# 檢查虛擬環境
if [ -d ".venv" ]; then
    echo -e "${GREEN}✓ 虛擬環境存在${NC}"
else
    echo -e "${RED}✗ 虛擬環境不存在${NC}"
    EXIT_CODE=1
fi

# 啟動虛擬環境
source .venv/bin/activate 2>/dev/null || true

# 檢查 Python 版本
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"

# 檢查 PyTorch
if python -c "import torch" 2>/dev/null; then
    TORCH_VERSION=$(python -c "import torch; print(torch.__version__)")
    echo -e "${GREEN}✓ PyTorch: $TORCH_VERSION${NC}"

    # 檢查 CUDA
    if python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
        CUDA_VERSION=$(python -c "import torch; print(torch.version.cuda)")
        GPU_NAME=$(python -c "import torch; print(torch.cuda.get_device_name(0))")
        COMPUTE_CAP=$(python -c "import torch; cap=torch.cuda.get_device_capability(0); print(f'{cap[0]}.{cap[1]}')")
        echo -e "${GREEN}✓ CUDA: $CUDA_VERSION${NC}"
        echo -e "${GREEN}✓ GPU: $GPU_NAME${NC}"
        echo -e "${GREEN}✓ Compute Capability: $COMPUTE_CAP${NC}"

        if [[ $COMPUTE_CAP == "12.0" ]]; then
            echo -e "${BLUE}  → Blackwell 架構 (sm_120) 支援正常${NC}"
        fi
    else
        echo -e "${YELLOW}! CUDA 不可用 (僅 CPU 模式)${NC}"
        echo -e "${YELLOW}  這在 WSL2 可能是 GPU passthrough 問題${NC}"
        EXIT_CODE=1
    fi
else
    echo -e "${RED}✗ PyTorch 未安裝${NC}"
    EXIT_CODE=1
fi

# 檢查 SageAttention
if python -c "import sageattention" 2>/dev/null; then
    SAGE_VERSION=$(python -c "import sageattention; print(sageattention.__version__ if hasattr(sageattention, '__version__') else 'installed')" 2>/dev/null || echo "installed")
    echo -e "${GREEN}✓ SageAttention: $SAGE_VERSION${NC}"
else
    echo -e "${RED}✗ SageAttention 未安裝${NC}"
    EXIT_CODE=1
fi

# 檢查 Flash Attention (可選)
if python -c "import flash_attn" 2>/dev/null; then
    FLASH_VERSION=$(python -c "import flash_attn; print(flash_attn.__version__)" 2>/dev/null || echo "installed")
    echo -e "${GREEN}✓ Flash Attention: $FLASH_VERSION${NC}"
else
    echo -e "${YELLOW}  Flash Attention 未安裝 (可選,將使用 SageAttention)${NC}"
fi

# 檢查 Triton
if python -c "import triton" 2>/dev/null; then
    TRITON_VERSION=$(python -c "import triton; print(triton.__version__)")
    echo -e "${GREEN}✓ Triton: $TRITON_VERSION${NC}"

    if python -c "import triton; v=triton.__version__.split('.'); exit(0 if (int(v[0])>3 or (int(v[0])==3 and int(v[1])>=3)) else 1)" 2>/dev/null; then
        echo -e "${BLUE}  → Triton 3.3+ 支援 Blackwell 架構${NC}"
    else
        echo -e "${YELLOW}  ! Triton 版本 < 3.3,可能缺少 Blackwell 優化${NC}"
    fi
else
    echo -e "${YELLOW}! Triton 未安裝${NC}"
fi

# 檢查 ComfyUI
if [ -d "../ComfyUI" ]; then
    echo -e "${GREEN}✓ ComfyUI 目錄存在${NC}"
else
    echo -e "${RED}✗ ComfyUI 目錄不存在${NC}"
    EXIT_CODE=1
fi

# 檢查 symlink
if [ -L "../ComfyUI/custom_nodes/comfyui-civitai-alchemist" ]; then
    echo -e "${GREEN}✓ Custom node symlink 已建立${NC}"
else
    echo -e "${YELLOW}! Custom node symlink 未建立${NC}"
fi

# 檢查環境變數
echo ""
echo "環境變數檢查:"
if [ -n "$CUDA_MODULE_LOADING" ]; then
    echo -e "${GREEN}✓ CUDA_MODULE_LOADING=$CUDA_MODULE_LOADING${NC}"
else
    echo -e "${YELLOW}  CUDA_MODULE_LOADING 未設置 (將在 run_comfyui.sh 中自動載入)${NC}"
fi

if [ -n "$TORCH_CUDA_ARCH_LIST" ]; then
    echo -e "${GREEN}✓ TORCH_CUDA_ARCH_LIST=$TORCH_CUDA_ARCH_LIST${NC}"
else
    echo -e "${YELLOW}  TORCH_CUDA_ARCH_LIST 未設置 (將在 run_comfyui.sh 中自動載入)${NC}"
fi

# WSL2 特定檢查
echo ""
echo "WSL2 檢查:"
if command -v nvidia-smi >/dev/null 2>&1; then
    echo -e "${GREEN}✓ nvidia-smi 可用 (GPU passthrough 正常)${NC}"
else
    echo -e "${RED}✗ nvidia-smi 不可用 (GPU passthrough 有問題)${NC}"
    EXIT_CODE=1
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=== 環境檢查完成 - 一切正常! ===${NC}"
else
    echo -e "${YELLOW}=== 環境檢查完成 - 發現一些問題 ===${NC}"
    echo -e "${YELLOW}請檢查上面標記為 ✗ 或 ! 的項目${NC}"
fi

exit $EXIT_CODE
