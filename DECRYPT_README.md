# 百度网盘加密文件解密工具使用说明

这个工具用于解密使用 BaiduEncryptSync 加密上传的文件。它可以解密单个文件或整个目录中的所有加密文件。

## 准备工作

1. 确保已安装 Python 3.6 或更高版本
2. 安装必要的依赖库：
   ```
   pip install pycryptodome tqdm
   ```

## 使用方法

### 解密单个文件

```bash
python decrypt_files.py -f /path/to/encrypted_file -p 您的密码
```

如果您使用的是默认密码 (123456)，可以省略密码参数：
```bash
python decrypt_files.py -f /path/to/encrypted_file
```

指定输出文件路径：
```bash
python decrypt_files.py -f /path/to/encrypted_file -o /path/to/output_file -p 您的密码
```

### 解密整个目录

解密目录中的所有加密文件：
```bash
python decrypt_files.py -d /path/to/directory -p 您的密码
```

递归解密目录及其子目录中的所有加密文件：
```bash
python decrypt_files.py -d /path/to/directory -p 您的密码 -r
```

保留原始加密文件（默认会删除原始加密文件）：
```bash
python decrypt_files.py -d /path/to/directory -p 您的密码 -k
```

## 参数说明

- `-f, --file`: 要解密的单个文件路径
- `-d, --directory`: 包含加密文件的目录路径
- `-p, --password`: 解密密码，默认为 "123456"
- `-o, --output`: 输出文件路径（仅适用于单个文件解密）
- `-r, --recursive`: 递归处理子目录中的文件
- `-k, --keep`: 保留原始加密文件（默认会删除原始文件）

## 常见问题

1. **如何知道文件是否加密？**
   - 加密文件通常比原始文件略大，至少多32字节
   - 解密工具会自动检测并跳过非加密文件

2. **忘记密码怎么办？**
   - 如果您忘记了加密密码，将无法恢复文件内容
   - 建议始终使用可记忆的密码并妥善保管

3. **解密后的文件名是什么？**
   - 如果原文件名以 .enc 结尾，解密后会去除这个后缀
   - 否则，解密后的文件将添加 .dec 后缀

4. **为什么某些文件解密失败？**
   - 密码可能不正确
   - 文件可能已损坏
   - 文件可能不是使用此工具加密的

## 示例

解密单个文件：
```bash
python decrypt_files.py -f /home/user/downloads/secret_document.pdf.enc -p my-secret-password
```

解密整个下载目录：
```bash
python decrypt_files.py -d /home/user/downloads -p my-secret-password -r
```

## 安全提示

- 请在安全的环境中执行解密操作
- 如果文件包含敏感信息，解密后应妥善保管
- 不要在不信任的计算机上输入您的解密密码
