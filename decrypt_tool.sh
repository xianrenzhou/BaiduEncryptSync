#!/bin/bash
# 百度网盘加密文件解密工具 - Shell脚本
# 此脚本简化了解密工具的使用，适用于Linux/Mac用户

echo "================================================"
echo "        百度网盘加密文件解密工具 - 快速启动"
echo "================================================"
echo ""

# 检查Python是否已安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未检测到Python！请先安装Python 3.6或更高版本。"
    echo "对于Ubuntu/Debian：sudo apt-get install python3 python3-pip"
    echo "对于CentOS/RHEL：sudo yum install python3 python3-pip"
    echo "对于Mac：brew install python3"
    echo ""
    exit 1
fi

# 检查依赖项是否已安装
if ! python3 -c "import Crypto" &> /dev/null; then
    echo "正在安装必要的依赖库..."
    pip3 install pycryptodome tqdm
    if [ $? -ne 0 ]; then
        echo "安装依赖失败，请手动运行: pip3 install pycryptodome tqdm"
        exit 1
    fi
fi

echo "请选择解密模式："
echo "1. 解密单个文件"
echo "2. 解密整个文件夹（不包含子文件夹）"
echo "3. 解密整个文件夹及其所有子文件夹"
echo ""

read -p "请输入选项 (1/2/3): " choice

if [ "$choice" = "1" ]; then
    # 解密单个文件
    echo ""
    read -p "请输入要解密的文件路径: " file_path
    read -p "请输入解密密码 (默认为123456，直接回车使用默认密码): " password
    
    if [ -z "$password" ]; then
        password="123456"
    fi
    
    echo ""
    echo "正在解密文件..."
    python3 decrypt_files.py -f "$file_path" -p "$password"
    
elif [ "$choice" = "2" ]; then
    # 解密整个文件夹（不递归）
    echo ""
    read -p "请输入要解密的文件夹路径: " dir_path
    read -p "请输入解密密码 (默认为123456，直接回车使用默认密码): " password
    
    if [ -z "$password" ]; then
        password="123456"
    fi
    
    echo ""
    echo "是否保留原始加密文件？"
    read -p "请选择 (y/n，默认n): " keep
    
    if [ "$keep" = "y" ] || [ "$keep" = "Y" ]; then
        echo "正在解密文件夹中的文件 (保留原始文件)..."
        python3 decrypt_files.py -d "$dir_path" -p "$password" -k
    else
        echo "正在解密文件夹中的文件..."
        python3 decrypt_files.py -d "$dir_path" -p "$password"
    fi
    
elif [ "$choice" = "3" ]; then
    # 解密整个文件夹（递归）
    echo ""
    read -p "请输入要解密的文件夹路径: " dir_path
    read -p "请输入解密密码 (默认为123456，直接回车使用默认密码): " password
    
    if [ -z "$password" ]; then
        password="123456"
    fi
    
    echo ""
    echo "是否保留原始加密文件？"
    read -p "请选择 (y/n，默认n): " keep
    
    if [ "$keep" = "y" ] || [ "$keep" = "Y" ]; then
        echo "正在递归解密文件夹及其子文件夹中的文件 (保留原始文件)..."
        python3 decrypt_files.py -d "$dir_path" -p "$password" -r -k
    else
        echo "正在递归解密文件夹及其子文件夹中的文件..."
        python3 decrypt_files.py -d "$dir_path" -p "$password" -r
    fi
    
else
    echo "无效的选项！"
    exit 1
fi

echo ""
echo "操作完成！"
