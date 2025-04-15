#!/bin/bash

# 开发恢复脚本
# 用于在开发中断后恢复开发

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
# 元数据文件路径
METADATA_FILE="${PROJECT_ROOT}/.segment_status"

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

# 显示元数据文件内容
show_metadata() {
    if [ -f "$METADATA_FILE" ]; then
        print_message "$BLUE" "元数据文件内容:"
        cat "$METADATA_FILE"
    else
        print_message "$YELLOW" "元数据文件不存在: $METADATA_FILE"
    fi
}

# 恢复开发
resume_development() {
    print_message "$GREEN" "=== CodeInterpreter AI 开发恢复流程 ==="
    echo ""
    
    # 步骤1: 检查元数据文件
    print_message "$BLUE" "步骤1: 检查元数据文件"
    if [ -f "$METADATA_FILE" ]; then
        print_message "$GREEN" "元数据文件存在: $METADATA_FILE"
        show_metadata
    else
        print_message "$YELLOW" "元数据文件不存在，将创建初始文件"
        "$RECOVERY_SCRIPT" > /dev/null
        show_metadata
    fi
    echo ""
    
    # 步骤2: 检查文件完整性
    print_message "$BLUE" "步骤2: 检查文件完整性"
    "$RECOVERY_SCRIPT" check
    echo ""
    
    # 步骤3: 显示开发状态
    print_message "$BLUE" "步骤3: 显示开发状态"
    "$RECOVERY_SCRIPT" status
    echo ""
    
    # 步骤4: 提供恢复建议
    print_message "$BLUE" "步骤4: 恢复建议"
    
    # 获取最后一个完成的段落
    local last_completed=$(jq -r '.segments | to_entries[] | select(.value.status=="completed") | .key' "$METADATA_FILE" 2>/dev/null | sort | tail -n 1)
    
    # 获取进行中的段落
    local in_progress=$(jq -r '.segments | to_entries[] | select(.value.status=="in-progress") | .key' "$METADATA_FILE" 2>/dev/null | sort)
    
    if [ -n "$in_progress" ]; then
        print_message "$YELLOW" "发现进行中的段落: $in_progress"
        print_message "$GREEN" "建议: 继续完成进行中的段落"
    elif [ -n "$last_completed" ]; then
        # 提取段落ID中的数字部分
        local segment_num=$(echo "$last_completed" | sed 's/[^0-9]//g')
        local next_segment="S$((segment_num + 1))"
        
        print_message "$GREEN" "最后完成的段落: $last_completed"
        print_message "$GREEN" "建议: 开始开发下一个段落 $next_segment"
    else
        print_message "$YELLOW" "未找到已完成或进行中的段落"
        print_message "$GREEN" "建议: 从第一个段落(S1)开始开发"
    fi
    echo ""
    
    print_message "$GREEN" "=== 开发恢复流程完成 ==="
    echo ""
    print_message "$BLUE" "您可以使用以下命令来更新段落状态:"
    echo "  ./update_segment.sh <段落ID> <状态> [描述]"
    echo ""
    print_message "$BLUE" "例如:"
    echo "  ./update_segment.sh S1 in-progress \"开始开发API接口\""
    echo "  ./update_segment.sh S1 completed \"完成API接口开发\""
    echo ""
}

# 主函数
main() {
    resume_development
}

# 执行主函数
main "$@"
