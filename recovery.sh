#!/bin/bash

# 恢复提示词脚本 (优化版)
# 用于CodeInterpreter AI项目的分段式开发恢复

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 元数据文件路径
METADATA_FILE="${PROJECT_ROOT}/.segment_status"

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_message "$RED" "错误: 未找到命令 '$1'，请安装后再试。"
        exit 1
    fi
}

# 检查必要的命令
check_command "jq"
check_command "shasum"

# 初始化元数据文件
initialize_metadata() {
    if [ ! -f "$METADATA_FILE" ]; then
        print_message "$YELLOW" "元数据文件不存在，正在创建初始文件..."
        echo '{
            "project_name": "CodeInterpreter AI",
            "last_updated": "'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'",
            "segments": {},
            "files": {}
        }' > "$METADATA_FILE"
        print_message "$GREEN" "元数据文件已创建: $METADATA_FILE"
    else
        print_message "$BLUE" "元数据文件已存在: $METADATA_FILE"
    fi
}

# 计算文件哈希值
calculate_file_hash() {
    local file_path=$1
    if [ -f "$file_path" ]; then
        shasum -a 256 "$file_path" | cut -d ' ' -f 1
    else
        echo ""
    fi
}

# 扫描项目文件并更新元数据
scan_project_files() {
    print_message "$BLUE" "扫描项目文件..."
    
    # 获取所有源代码文件
    local files=$(find "$PROJECT_ROOT" -type f \
        -not -path "*/\.*" \
        -not -path "*/node_modules/*" \
        -not -path "*/venv/*" \
        -not -path "*/dist/*" \
        -not -path "*/build/*" \
        -not -name "*.pyc" \
        -not -name "recovery.sh" \
        | sort)
    
    # 临时文件用于存储更新后的元数据
    local temp_file=$(mktemp)
    
    # 读取当前元数据
    cat "$METADATA_FILE" > "$temp_file"
    
    # 更新文件哈希值
    for file in $files; do
        local rel_path="${file#$PROJECT_ROOT/}"
        local hash=$(calculate_file_hash "$file")
        
        # 使用jq更新文件哈希
        jq --arg path "$rel_path" --arg hash "$hash" --arg time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
           '.files[$path] = {"hash": $hash, "last_updated": $time}' "$temp_file" > "${temp_file}.new"
        mv "${temp_file}.new" "$temp_file"
    done
    
    # 更新最后更新时间
    jq --arg time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" '.last_updated = $time' "$temp_file" > "${temp_file}.new"
    mv "${temp_file}.new" "$temp_file"
    
    # 替换原始元数据文件
    mv "$temp_file" "$METADATA_FILE"
    
    print_message "$GREEN" "项目文件扫描完成，元数据已更新。"
}

# 检查文件完整性
check_file_integrity() {
    print_message "$BLUE" "检查文件完整性..."
    
    local integrity_issues=0
    
    # 从元数据中获取所有文件
    local files=$(jq -r '.files | keys[]' "$METADATA_FILE")
    
    for file in $files; do
        local full_path="${PROJECT_ROOT}/${file}"
        
        # 检查文件是否存在
        if [ ! -f "$full_path" ]; then
            print_message "$RED" "文件丢失: $file"
            integrity_issues=$((integrity_issues + 1))
            continue
        fi
        
        # 获取存储的哈希值
        local stored_hash=$(jq -r ".files[\"$file\"].hash" "$METADATA_FILE")
        
        # 计算当前哈希值
        local current_hash=$(calculate_file_hash "$full_path")
        
        # 比较哈希值
        if [ "$stored_hash" != "$current_hash" ]; then
            print_message "$RED" "文件已修改: $file"
            print_message "$YELLOW" "  存储的哈希值: $stored_hash"
            print_message "$YELLOW" "  当前哈希值: $current_hash"
            integrity_issues=$((integrity_issues + 1))
        fi
    done
    
    if [ $integrity_issues -eq 0 ]; then
        print_message "$GREEN" "所有文件完整性检查通过。"
    else
        print_message "$RED" "发现 $integrity_issues 个文件完整性问题。"
    fi
}

# 更新段落状态
update_segment_status() {
    local segment_id=$1
    local status=$2
    local description=$3
    
    if [ -z "$segment_id" ] || [ -z "$status" ]; then
        print_message "$RED" "错误: 段落ID和状态不能为空。"
        echo "用法: $0 update-segment <段落ID> <状态> [描述]"
        exit 1
    fi
    
    print_message "$BLUE" "更新段落状态: $segment_id -> $status"
    
    # 使用jq更新段落状态
    jq --arg id "$segment_id" \
       --arg status "$status" \
       --arg desc "$description" \
       --arg time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
       '.segments[$id] = {"status": $status, "description": $desc, "last_updated": $time}' \
       "$METADATA_FILE" > "${METADATA_FILE}.new"
    
    mv "${METADATA_FILE}.new" "$METADATA_FILE"
    
    # 同时更新文件哈希值
    scan_project_files
    
    print_message "$GREEN" "段落状态已更新: $segment_id -> $status"
}

# 获取开发状态摘要
get_development_status() {
    print_message "$BLUE" "获取开发状态摘要..."
    
    # 获取所有段落
    local segments=$(jq -r '.segments | keys[]' "$METADATA_FILE" 2>/dev/null)
    
    if [ -z "$segments" ]; then
        print_message "$YELLOW" "尚未记录任何段落状态。"
    else
        print_message "$GREEN" "段落状态摘要:"
        echo "----------------------------------------"
        echo "段落ID | 状态 | 最后更新时间 | 描述"
        echo "----------------------------------------"
        
        for segment in $segments; do
            local status=$(jq -r ".segments[\"$segment\"].status" "$METADATA_FILE")
            local updated=$(jq -r ".segments[\"$segment\"].last_updated" "$METADATA_FILE")
            local desc=$(jq -r ".segments[\"$segment\"].description" "$METADATA_FILE")
            
            # 格式化日期时间
            local formatted_date=$(date -jf "%Y-%m-%dT%H:%M:%SZ" "$updated" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$updated")
            
            printf "%-8s | %-6s | %-16s | %s\n" "$segment" "$status" "$formatted_date" "$desc"
        done
        echo "----------------------------------------"
    fi
    
    # 显示最后更新时间
    local last_updated=$(jq -r '.last_updated' "$METADATA_FILE")
    local formatted_last_updated=$(date -jf "%Y-%m-%dT%H:%M:%SZ" "$last_updated" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$last_updated")
    print_message "$BLUE" "元数据最后更新时间: $formatted_last_updated"
}

# 主函数
main() {
    # 确保元数据文件存在
    initialize_metadata
    
    # 处理命令行参数
    case "$1" in
        "scan")
            scan_project_files
            ;;
        "check")
            check_file_integrity
            ;;
        "update-segment")
            update_segment_status "$2" "$3" "$4"
            ;;
        "status")
            get_development_status
            ;;
        *)
            print_message "$GREEN" "CodeInterpreter AI 项目恢复工具 (优化版)"
            echo ""
            echo "用法: $0 <命令> [参数]"
            echo ""
            echo "可用命令:"
            echo "  scan                  扫描项目文件并更新元数据"
            echo "  check                 检查文件完整性"
            echo "  update-segment <ID> <状态> [描述]  更新段落状态"
            echo "  status                获取开发状态摘要"
            echo ""
            echo "示例:"
            echo "  $0 scan"
            echo "  $0 update-segment S1 completed \"完成了基础API实现\""
            echo "  $0 status"
            ;;
    esac
}

# 执行主函数
main "$@"
