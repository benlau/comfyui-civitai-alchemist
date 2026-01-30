#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CUSTOM_NODE_DIR="../ComfyUI/custom_nodes/comfyui-civitai-alchemist"

echo -e "${YELLOW}建立 symlink 到 ComfyUI...${NC}"

# 移除舊連結
if [ -L "$CUSTOM_NODE_DIR" ]; then
    rm "$CUSTOM_NODE_DIR"
    echo "移除舊連結"
fi

# 建立新連結
ln -s "$(pwd)" "$CUSTOM_NODE_DIR"

echo -e "${GREEN}✓ Symlink 建立完成:${NC}"
echo "  $(pwd)"
echo "  → $CUSTOM_NODE_DIR"
