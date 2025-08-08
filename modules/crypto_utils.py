#!/usr/bin/env python3
"""
加密和解密工具模块
提供文件内容加密和解密功能
"""
import os
import io
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

def derive_key(password, salt=None, iterations=100000):
    """
    从密码派生加密密钥
    
    Args:
        password (str): 用户提供的密码
        salt (bytes, optional): 盐值，如果不提供则随机生成
        iterations (int): 迭代次数
        
    Returns:
        tuple: (key, salt)
    """
    if salt is None:
        salt = os.urandom(16)  # 生成16字节的随机盐值
    
    # 使用 PBKDF2 从密码派生密钥
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations, dklen=32)
    
    return key, salt

def encrypt_data(data, password="123456"):
    """
    加密数据
    
    Args:
        data (bytes): 要加密的数据
        password (str): 加密密码，默认为123456
        
    Returns:
        bytes: 加密后的数据（格式：salt + iv + 加密数据）
    """
    # 派生密钥
    key, salt = derive_key(password)
    
    # 生成随机初始化向量
    iv = os.urandom(16)
    
    # 创建AES加密器（CBC模式）
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    # 对数据进行填充并加密
    padded_data = pad(data, AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    
    # 组合salt、iv和加密数据
    # 格式：16字节salt + 16字节iv + 加密数据
    result = salt + iv + encrypted_data
    
    return result

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
    key, _ = derive_key(password, salt)
    
    # 创建AES解密器
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    # 解密数据并去除填充
    decrypted_padded_data = cipher.decrypt(actual_encrypted_data)
    decrypted_data = unpad(decrypted_padded_data, AES.block_size)
    
    return decrypted_data

def encrypt_file(input_file_path, output_file_path=None, password="123456"):
    """
    加密文件
    
    Args:
        input_file_path (str): 输入文件路径
        output_file_path (str, optional): 输出文件路径，如果不提供则在原文件名后加.enc
        password (str): 加密密码，默认为123456
        
    Returns:
        str: 加密后的文件路径
    """
    if not output_file_path:
        output_file_path = input_file_path + '.enc'
    
    # 读取文件内容
    with open(input_file_path, 'rb') as f:
        data = f.read()
    
    # 加密数据
    encrypted_data = encrypt_data(data, password)
    
    # 写入加密文件
    with open(output_file_path, 'wb') as f:
        f.write(encrypted_data)
    
    return output_file_path

def decrypt_file(input_file_path, output_file_path=None, password="123456"):
    """
    解密文件
    
    Args:
        input_file_path (str): 输入加密文件路径
        output_file_path (str, optional): 输出解密文件路径，如果不提供则去掉.enc后缀
        password (str): 解密密码，默认为123456
        
    Returns:
        str: 解密后的文件路径
    """
    if not output_file_path:
        if input_file_path.endswith('.enc'):
            output_file_path = input_file_path[:-4]  # 去掉.enc后缀
        else:
            output_file_path = input_file_path + '.dec'
    
    # 读取加密文件内容
    with open(input_file_path, 'rb') as f:
        encrypted_data = f.read()
    
    # 解密数据
    decrypted_data = decrypt_data(encrypted_data, password)
    
    # 写入解密文件
    with open(output_file_path, 'wb') as f:
        f.write(decrypted_data)
    
    return output_file_path

def encrypt_bytes_stream(data, password="123456"):
    """
    加密字节流，返回字节流对象
    
    Args:
        data (bytes): 要加密的字节数据
        password (str): 加密密码，默认为123456
        
    Returns:
        BytesIO: 包含加密数据的字节流对象
    """
    encrypted_data = encrypt_data(data, password)
    return io.BytesIO(encrypted_data)

def decrypt_bytes_stream(encrypted_stream, password="123456"):
    """
    解密字节流，返回字节流对象
    
    Args:
        encrypted_stream (BytesIO/bytes): 加密的字节流或字节数据
        password (str): 解密密码，默认为123456
        
    Returns:
        BytesIO: 包含解密数据的字节流对象
    """
    if isinstance(encrypted_stream, io.BytesIO):
        encrypted_stream.seek(0)
        encrypted_data = encrypted_stream.read()
    else:
        encrypted_data = encrypted_stream
    
    decrypted_data = decrypt_data(encrypted_data, password)
    return io.BytesIO(decrypted_data)


# 实用工具函数
def create_decrypt_script(file_path, output_dir=None, password="123456"):
    """
    为加密文件创建一个简单的解密脚本
    
    Args:
        file_path (str): 加密文件路径
        output_dir (str, optional): 脚本输出目录，默认与加密文件在同一目录
        password (str): 解密密码，默认为123456
        
    Returns:
        str: 解密脚本路径
    """
    file_name = os.path.basename(file_path)
    file_dir = os.path.dirname(file_path) or '.'
    
    if not output_dir:
        output_dir = file_dir
    
    script_path = os.path.join(output_dir, f"decrypt_{file_name}.py")
    
    with open(script_path, 'w') as f:
        f.write(f'''#!/usr/bin/env python3
"""
{file_name} 解密脚本
使用方法: python decrypt_{file_name}.py [输出文件路径]
"""
import os
import sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import hashlib

def derive_key(password, salt, iterations=100000):
    """从密码派生密钥"""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations, dklen=32)

def decrypt_file(input_file, output_file=None, password="{password}"):
    """解密文件"""
    if not output_file:
        if input_file.endswith('.enc'):
            output_file = input_file[:-4]
        else:
            output_file = input_file + '.dec'
    
    with open(input_file, 'rb') as f:
        data = f.read()
    
    # 提取salt和iv
    salt = data[:16]
    iv = data[16:32]
    encrypted_data = data[32:]
    
    # 派生密钥
    key = derive_key(password, salt)
    
    # 解密数据
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_padded = cipher.decrypt(encrypted_data)
    decrypted = unpad(decrypted_padded, AES.block_size)
    
    with open(output_file, 'wb') as f:
        f.write(decrypted)
    
    print(f"文件已解密到: {{output_file}}")
    return output_file

if __name__ == "__main__":
    input_file = "{file_path}"
    
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
        decrypt_file(input_file, output_file)
    else:
        decrypt_file(input_file)
''')
    
    # 设置可执行权限
    os.chmod(script_path, 0o755)
    
    return script_path

if __name__ == "__main__":
    # 简单测试
    test_data = b"This is a test message for encryption and decryption."
    password = "test-password"
    
    print("原始数据:", test_data.decode())
    
    # 加密
    encrypted = encrypt_data(test_data, password)
    print("加密后数据长度:", len(encrypted))
    
    # 解密
    decrypted = decrypt_data(encrypted, password)
    print("解密后数据:", decrypted.decode())
    
    # 验证
    assert test_data == decrypted, "加密解密不匹配！"
    print("加密解密测试通过！")
