#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

CUSTOM_NODE_DIR="../ComfyUI/custom_nodes/comfyui-civitai-alchemist"

if [ -L "$CUSTOM_NODE_DIR" ]; then
    rm "$CUSTOM_NODE_DIR"
    echo -e "${GREEN}✓ Symlink 已移除${NC}"
else
    echo -e "${RED}找不到 symlink${NC}"
fi
