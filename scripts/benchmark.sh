#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=== ComfyUI Attention Backend 性能測試 ==="
echo ""

# 啟動虛擬環境
source .venv/bin/activate

echo -e "${BLUE}檢測可用的 Attention backends:${NC}"
echo ""

# 檢查 SageAttention
if python -c "import sageattention" 2>/dev/null; then
    echo -e "${GREEN}✓ SageAttention 可用${NC}"
    HAS_SAGE=1
else
    echo -e "${YELLOW}✗ SageAttention 不可用${NC}"
    HAS_SAGE=0
fi

# 檢查 Flash Attention
if python -c "import flash_attn" 2>/dev/null; then
    echo -e "${GREEN}✓ Flash Attention 可用${NC}"
    HAS_FLASH=1
else
    echo -e "${YELLOW}✗ Flash Attention 不可用${NC}"
    HAS_FLASH=0
fi

# PyTorch SDPA 總是可用 (PyTorch 2.0+)
echo -e "${GREEN}✓ PyTorch SDPA 可用 (baseline)${NC}"

echo ""
echo -e "${BLUE}ComfyUI 會按以下優先順序自動選擇:${NC}"
echo "  1. Flash Attention v3 (如果可用)"
echo "  2. Flash Attention v2 (如果可用)"
echo "  3. SageAttention (如果可用)"
echo "  4. PyTorch SDPA"
echo "  5. xFormers (如果可用)"
echo ""

# 顯示預期使用的 backend
if [ $HAS_FLASH -eq 1 ]; then
    echo -e "${GREEN}→ ComfyUI 預期會使用: Flash Attention${NC}"
elif [ $HAS_SAGE -eq 1 ]; then
    echo -e "${GREEN}→ ComfyUI 預期會使用: SageAttention${NC}"
else
    echo -e "${YELLOW}→ ComfyUI 預期會使用: PyTorch SDPA${NC}"
fi

echo ""
echo -e "${BLUE}性能參考 (相對於無優化):${NC}"
echo "  • SageAttention: ${GREEN}1.5-2.0x 加速${NC}"
echo "  • Flash Attention: ${GREEN}1.5-2.0x 加速${NC}"
echo "  • PyTorch SDPA: ${GREEN}1.2-1.5x 加速${NC}"
echo ""

echo -e "${YELLOW}提示: 要查看實際使用的 backend,請啟動 ComfyUI 並檢查 console 輸出${NC}"
echo -e "${YELLOW}執行: bash scripts/run_comfyui.sh${NC}"
echo ""

# 簡單的 GPU 記憶體和運算測試
echo -e "${BLUE}執行簡單的 GPU 測試...${NC}"
python << 'EOF'
import torch
import time

if torch.cuda.is_available():
    device = torch.device("cuda")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"記憶體: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    # 簡單的矩陣運算測試
    size = 4096
    print(f"\n執行 {size}x{size} 矩陣乘法測試...")

    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)

    # Warm up
    for _ in range(3):
        c = torch.matmul(a, b)
    torch.cuda.synchronize()

    # Benchmark
    start = time.time()
    for _ in range(10):
        c = torch.matmul(a, b)
    torch.cuda.synchronize()
    elapsed = time.time() - start

    tflops = (2 * size**3 * 10) / elapsed / 1e12
    print(f"效能: {tflops:.2f} TFLOPS")
    print(f"平均時間: {elapsed/10*1000:.2f} ms")
else:
    print("CUDA 不可用")
EOF

echo ""
echo -e "${GREEN}=== 測試完成 ===${NC}"
