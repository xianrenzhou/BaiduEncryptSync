# 百度网盘加密上传工具使用说明

本工具为百度网盘上传工具的扩展版本，增加了文件内容加密功能。上传的文件在网盘中是加密存储的，只有知道密钥的人才能解密查看文件内容。

## 主要功能

1. **常规上传**：与原来一样，上传文件到百度网盘。
2. **加密上传**：将文件内容加密后上传，文件名保持不变。
3. **批量上传**：支持多线程并行上传多个文件。
4. **文件下载**：从百度网盘下载文件。
5. **文件解密**：下载并解密加密文件。

## 依赖安装

```bash
pip install pycryptodome tqdm requests
```

## 使用方法

### 1. 加密上传文件

在上传文件时指定加密参数：

```python
from modules.upload_new import encrypt_upload

# 使用默认密码(123456)加密上传
result = encrypt_upload(
    access_token="your_access_token",
    local_file_path="./your_file.zip",
    remote_path="/apps/your_app/your_file.zip"
)

# 使用自定义密码加密上传
result = encrypt_upload(
    access_token="your_access_token",
    local_file_path="./your_file.zip",
    remote_path="/apps/your_app/your_file.zip",
    password="your-secure-password"  # 自定义密码
)
```

### 2. 下载并解密文件

```python
from modules.decrypt_download import download_and_decrypt

# 使用默认密码(123456)下载并解密
decrypted_file_path = download_and_decrypt(
    access_token="your_access_token",
    file_path="/apps/your_app/your_file.zip",
    output_path="./your_file_decrypted.zip"
)

# 使用自定义密码下载并解密
decrypted_file_path = download_and_decrypt(
    access_token="your_access_token",
    file_path="/apps/your_app/your_file.zip",
    password="your-secure-password",  # 与加密时使用的密码一致
    output_path="./your_file_decrypted.zip"
)
```

### 3. 命令行使用

可以使用命令行工具下载和解密文件：

```bash
# 仅下载文件
python modules/decrypt_download.py "/apps/your_app/your_file.zip" --token "your_access_token" --output "./your_file.zip"

# 下载并解密文件
python modules/decrypt_download.py "/apps/your_app/your_file.zip" --token "your_access_token" --output "./your_file.zip" --decrypt --password "your-secure-password"
```

## 加密原理

1. 文件加密使用 AES-256-CBC 加密算法
2. 密钥使用 PBKDF2 从用户密码派生，加入随机盐值增强安全性
3. 加密数据格式：16字节salt + 16字节iv + 加密数据

## 安全注意事项

1. 请妥善保管您的加密密码，一旦丢失将无法恢复文件内容
2. 默认密码 "123456" 安全性较低，建议使用强密码
3. 加密文件名称在网盘中可见，只有文件内容是加密的
4. 本工具不会在任何地方存储您的密码

## 高级选项

- 调整 `chunk_size` 参数可以控制分片大小
- 调整 `max_workers` 参数可以控制并发上传的线程数
