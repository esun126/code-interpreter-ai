#!/bin/bash

# 段落更新脚本
# 用于在完成段落开发后更新状态

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 恢复脚本路径
RECOVERY_SCRIPT="${PROJECT_ROOT}/recovery.sh"

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 检查恢复脚本是否存在
if [ ! -f "$RECOVERY_SCRIPT" ]; then
    print_message "$RED" "错误: 恢复脚本不存在: $RECOVERY_SCRIPT"
    exit 1
fi

# 确保恢复脚本可执行
chmod +x "$RECOVERY_SCRIPT"

# 显示帮助信息
show_help() {
    print_message "$GREEN" "CodeInterpreter AI 段落更新工具"
    echo ""
    echo "此脚本用于在完成段落开发后更新状态，并同步更新元数据索引文件。"
    echo ""
    echo "用法: $0 <段落ID> <状态> [描述]"
    echo ""
    echo "参数:"
    echo "  <段落ID>   段落的唯一标识符，例如 S1, S2, S3 等"
    echo "  <状态>     段落的当前状态，例如 completed, in-progress, pending 等"
    echo "  [描述]     可选的段落描述，用于记录段落的详细信息"
    echo ""
    echo "示例:"
    echo "  $0 S1 completed \"完成了基础API实现\""
    echo "  $0 S2 in-progress \"正在开发用户界面\""
    echo ""
}

# 主函数
main() {
    # 检查参数
    if [ $# -lt 2 ]; then
        show_help
        exit 1
    fi
    
    local segment_id=$1
    local status=$2
    local description=$3
    
    print_message "$BLUE" "正在更新段落状态..."
    
    # 调用恢复脚本的update-segment命令
    "$RECOVERY_SCRIPT" update-segment "$segment_id" "$status" "$description"
    
    # 显示当前开发状态
    "$RECOVERY_SCRIPT" status
}

# 执行主函数
main "$@"
