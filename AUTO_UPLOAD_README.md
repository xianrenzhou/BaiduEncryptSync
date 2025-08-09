# 百度网盘自动加密上传工具使用说明

这个工具使用 inotify 监控指定目录，当有新文件添加时，自动将文件加密上传到百度网盘。

## 功能特点

- 实时监控目录变化，检测新增文件
- 支持递归监控子目录
- 支持文件内容加密（文件名不加密）
- 可设置冷却时间，避免上传未完成的文件
- 可按文件类型、大小和名称模式过滤
- 多线程上传，高效处理多个文件
- 自动使用和刷新百度网盘访问令牌

## 准备工作

1. 确保已安装 Python 3.6 或更高版本
2. 安装必要的依赖库：
   ```
   pip install pycryptodome pyinotify pyyaml tqdm
   ```
3. 确保 `config/config.yaml` 文件包含百度网盘应用的 AppID、AppKey、SecretKey 等信息

## 使用方法

### 基本用法

```bash
python main.py -d /path/to/watch
```

### 监控并加密上传

```bash
python main.py -d /path/to/watch -e -p "your-password"
```

### 完整参数说明

```
usage: main.py [-h] -d DIRECTORY [-r REMOTE_DIR] [-e] [-p PASSWORD] [-n]
               [-t FILE_TYPES] [-s MIN_SIZE] [-c COOLDOWN] [-x EXCLUDE]
               [-X EXCLUDE_DIRS] [-u] [-w WORKERS] [--auth-code AUTH_CODE]

百度网盘文件自动加密上传工具

optional arguments:
  -h, --help            显示帮助信息并退出
  -d DIRECTORY, --directory DIRECTORY
                        要监控的目录路径
  -r REMOTE_DIR, --remote-dir REMOTE_DIR
                        百度网盘中的目标目录，默认为/apps/autoSync
  -e, --encrypt         是否加密上传文件
  -p PASSWORD, --password PASSWORD
                        加密密码，默认为123456
  -n, --no-recursive    不递归监控子目录
  -t FILE_TYPES, --file-types FILE_TYPES
                        要监控的文件类型，逗号分隔，如'.jpg,.png,.pdf'
  -s MIN_SIZE, --min-size MIN_SIZE
                        最小文件大小(字节)，小于此大小的文件不会上传
  -c COOLDOWN, --cooldown COOLDOWN
                        文件冷却时间(秒)，新文件创建后等待此时间再上传
  -x EXCLUDE, --exclude EXCLUDE
                        要排除的文件名模式，逗号分隔，如'*.tmp,~*'
  -X EXCLUDE_DIRS, --exclude-dirs EXCLUDE_DIRS
                        要排除的目录名称或路径，逗号分隔，如'tmp,cache,.git'
  -u, --upload-existing 是否上传监控目录中已存在的文件
  -w WORKERS, --workers WORKERS
                        上传工作线程数，默认为3
  --auth-code AUTH_CODE
                        百度网盘授权码，如果提供则使用此授权码而不自动获取
```

## 使用示例

### 1. 监控下载目录，上传所有新文件

```bash
python main.py -d ~/Downloads -r /apps/my_downloads
```

### 2. 监控并加密上传图片

```bash
python main.py -d ~/Pictures -r /apps/my_pictures -e -p "secure-password" -t ".jpg,.png,.gif"
```

### 3. 监控文档目录，排除临时文件

```bash
python main.py -d ~/Documents -r /apps/my_docs -x "*.tmp,~*,*.bak"
```

### 4. 只上传大于1MB的视频文件

```bash
python main.py -d ~/Videos -r /apps/my_videos -t ".mp4,.mkv,.avi" -s 1048576
```

### 6. 使用预先获取的授权码

```bash
python main.py -d ~/Documents -r /apps/my_docs --auth-code "your-auth-code-here"
```

## 工作原理

1. 程序启动时获取百度网盘访问令牌
2. 创建上传工作线程和文件监控器
3. 检测到新文件时，将其添加到待处理列表
4. 等待冷却时间后，将文件加入上传队列
5. 上传工作线程处理队列中的文件
6. 上传完成后记录结果

## 注意事项

- 此工具依赖 Linux 的 inotify 机制，仅在 Linux 系统上可用
- 大文件上传需要较长时间，请确保程序在此期间保持运行
- 上传加密文件后，需要对应的密钥才能解密查看
- 程序通过冷却时间等待文件写入完成，但对于某些特殊情况可能需要调整此参数
- 使用 `--auth-code` 参数可以跳过浏览器交互授权流程，直接使用预先获取的授权码

## 故障排除

1. **无法监控目录**：确保有对目录的读取权限，并且 inotify 实例数量未超过系统限制
2. **文件未上传**：检查文件大小、类型是否符合过滤条件，以及冷却时间是否足够
3. **上传失败**：检查网络连接和百度网盘访问令牌是否有效
4. **"Too many open files"错误**：调整系统的 inotify 监控限制（/proc/sys/fs/inotify/max_user_watches）
