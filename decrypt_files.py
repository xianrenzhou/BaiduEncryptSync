#!/usr/bin/env python3
"""
百度网盘加密文件解密工具

功能：
1. 解密单个加密文件
2. 批量解密指定目录下的所有加密文件
3. 可选是否保留原始加密文件

使用方法：
python decrypt_files.py -f <文件路径> -p <密码>
python decrypt_files.py -d <目录路径> -p <密码> [--recursive] [--keep]
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path
from tqdm import tqdm

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
except ImportError:
    print("错误: 缺少必要的加密库。")
    print("请安装 PyCryptodome: pip install pycryptodome")
    sys.exit(1)

# 解密相关函数
def derive_key(password, salt, iterations=100000):
    """从密码派生密钥"""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations, dklen=32)

def decrypt_data(encrypted_data, password="123456"):
    """
    解密数据
    
    Args:
        encrypted_data (bytes): 加密的数据（格式：salt + iv + 加密数据）
        password (str): 解密密码，默认为123456
        
    Returns:
        bytes: 解密后的原始数据
    """
    # 从加密数据中提取salt和iv
    salt = encrypted_data[:16]
    iv = encrypted_data[16:32]
    actual_encrypted_data = encrypted_data[32:]
    
    # 派生密钥
    key = derive_key(password, salt)
    
    # 创建AES解密器
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    # 解密数据并去除填充
    decrypted_padded_data = cipher.decrypt(actual_encrypted_data)
    decrypted_data = unpad(decrypted_padded_data, AES.block_size)
    
    return decrypted_data

def is_encrypted_file(file_path):
    """
    简单检查文件是否可能是我们的加密文件
    加密文件的前32字节包含salt和iv
    """
    try:
        if os.path.getsize(file_path) < 48:  # 至少需要salt+iv+一些数据
            return False
        
        with open(file_path, 'rb') as f:
            # 读取前几个字节检查
            header = f.read(32)
            # 这里我们只是简单检查文件是否足够大
            # 实际上，我们可以添加更复杂的检查，如特定的文件标记
            return len(header) == 32
    except:
        return False

def decrypt_file(input_file_path, output_file_path=None, password="123456", keep_original=False):
    """
    解密单个文件
    
    Args:
        input_file_path (str): 输入加密文件路径
        output_file_path (str, optional): 输出解密文件路径，如果不提供则去掉.enc后缀
        password (str): 解密密码，默认为123456
        keep_original (bool): 是否保留原始加密文件
        
    Returns:
        bool: 解密是否成功
    """
    if not os.path.exists(input_file_path):
        print(f"错误: 文件不存在: {input_file_path}")
        return False
    
    if not is_encrypted_file(input_file_path):
        print(f"警告: 文件可能不是加密文件: {input_file_path}")
        return False
    
    # 确定输出路径
    if not output_file_path:
        if input_file_path.endswith('.enc'):
            output_file_path = input_file_path[:-4]  # 去掉.enc后缀
        else:
            # 在文件名后添加.dec作为后缀
            base_dir = os.path.dirname(input_file_path)
            filename = os.path.basename(input_file_path)
            output_file_path = os.path.join(base_dir, f"{filename}.dec")
    
    try:
        # 读取加密文件内容
        with open(input_file_path, 'rb') as f:
            encrypted_data = f.read()
        
        # 解密数据
        try:
            decrypted_data = decrypt_data(encrypted_data, password)
        except Exception as e:
            print(f"解密失败: {input_file_path} - {str(e)}")
            print("提示: 密码可能不正确，或者文件不是有效的加密文件")
            return False
        
        # 写入解密文件
        with open(output_file_path, 'wb') as f:
            f.write(decrypted_data)
        
        # 删除原始文件（如果不保留）
        if not keep_original:
            os.remove(input_file_path)
        
        return True
    
    except Exception as e:
        print(f"处理文件时出错: {input_file_path} - {str(e)}")
        return False

def decrypt_directory(directory_path, password="123456", recursive=False, keep_original=False):
    """
    解密目录中的所有加密文件
    
    Args:
        directory_path (str): 目录路径
        password (str): 解密密码，默认为123456
        recursive (bool): 是否递归处理子目录
        keep_original (bool): 是否保留原始加密文件
        
    Returns:
        tuple: (成功计数, 失败计数, 跳过计数)
    """
    if not os.path.isdir(directory_path):
        print(f"错误: 目录不存在: {directory_path}")
        return 0, 0, 0
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    # 获取所有文件
    if recursive:
        all_files = [str(p) for p in Path(directory_path).rglob('*') if p.is_file()]
    else:
        all_files = [str(p) for p in Path(directory_path).glob('*') if p.is_file()]
    
    print(f"在 {'及其子目录' if recursive else ''} 中发现 {len(all_files)} 个文件")
    
    # 使用tqdm创建进度条
    with tqdm(all_files, desc="解密进度") as pbar:
        for file_path in pbar:
            pbar.set_description(f"处理: {os.path.basename(file_path)}")
            
            if is_encrypted_file(file_path):
                result = decrypt_file(file_path, None, password, keep_original)
                if result:
                    success_count += 1
                else:
                    failed_count += 1
            else:
                skipped_count += 1
    
    return success_count, failed_count, skipped_count

def main():
    parser = argparse.ArgumentParser(description="百度网盘加密文件解密工具")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="要解密的单个文件路径")
    group.add_argument("-d", "--directory", help="包含加密文件的目录路径")
    
    parser.add_argument("-p", "--password", default="123456", help="解密密码，默认为123456")
    parser.add_argument("-o", "--output", help="输出文件路径（仅适用于单个文件解密）")
    parser.add_argument("-r", "--recursive", action="store_true", help="递归处理子目录")
    parser.add_argument("-k", "--keep", action="store_true", help="保留原始加密文件")
    
    args = parser.parse_args()
    
    if args.file:
        # 解密单个文件
        success = decrypt_file(args.file, args.output, args.password, args.keep)
        if success:
            output_path = args.output or (args.file[:-4] if args.file.endswith('.enc') else f"{args.file}.dec")
            print(f"✅ 文件解密成功: {output_path}")
        else:
            print(f"❌ 文件解密失败: {args.file}")
    
    elif args.directory:
        # 解密目录中的文件
        print(f"开始解密目录: {args.directory} {'(递归)' if args.recursive else ''}")
        success_count, failed_count, skipped_count = decrypt_directory(
            args.directory, args.password, args.recursive, args.keep
        )
        
        print("\n解密完成!")
        print(f"✅ 成功解密: {success_count} 个文件")
        if failed_count > 0:
            print(f"❌ 解密失败: {failed_count} 个文件")
        print(f"⏩ 跳过非加密文件: {skipped_count} 个文件")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"程序出错: {str(e)}")
        sys.exit(1)
