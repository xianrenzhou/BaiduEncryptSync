# Docker 使用说明

本项目提供了Docker支持，使您可以在任何支持Docker的环境中运行百度网盘文件自动加密上传工具。

## 前提条件

- 安装 [Docker](https://docs.docker.com/get-docker/)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/) (可选，但推荐)

## 快速开始

### 使用 Docker Compose (推荐)

1. 编辑 `docker-compose.yml` 文件，将 `/path/to/local/data` 修改为您要监控的实际目录路径
2. 根据需要调整环境变量
3. 启动服务：

```bash
docker-compose up -d
```

4. 查看日志：

```bash
docker-compose logs -f
```

### 使用 Docker 命令

如果您不想使用 Docker Compose，可以直接使用 Docker 命令：

```bash
# 构建镜像
docker build -t baidu-encrypt-sync .

# 运行容器
docker run -d \
  --name baidu-encrypt-sync \
  --network host \
  -v $(pwd)/config:/app/config \
  -v /path/to/local/data:/data \
  -e WATCH_DIR=/data \
  -e REMOTE_DIR=/apps/autoSync \
  -e ENCRYPT=false \
  -e PASSWORD=123456 \
  baidu-encrypt-sync
```

## 环境变量

您可以通过环境变量自定义应用程序的行为：

| 环境变量 | 描述 | 默认值 |
|---------|------|-------|
| WATCH_DIR | 要监控的目录路径 | /data |
| REMOTE_DIR | 百度网盘中的目标目录 | /apps/autoSync |
| ENCRYPT | 是否加密上传文件 | false |
| PASSWORD | 加密密码 | 123456 |
| RECURSIVE | 是否递归监控子目录 | true |
| MIN_SIZE | 最小文件大小(字节) | 0 |
| COOLDOWN | 文件冷却时间(秒) | 2 |
| UPLOAD_EXISTING | 是否上传监控目录中已存在的文件 | false |
| WORKERS | 上传工作线程数 | 3 |
| FILE_TYPES | 要监控的文件类型，逗号分隔 | (不设置则监控所有类型) |
| EXCLUDE | 要排除的文件名模式，逗号分隔 | (不设置则不排除任何文件) |
| EXCLUDE_DIRS | 要排除的目录名称或路径，逗号分隔 | (不设置则不排除任何目录) |
| AUTH_CODE | 百度网盘授权码，如果提供则使用此授权码而不自动获取 | (不设置则自动获取授权码) |

## 数据卷

- `/app/config`: 存储配置文件的目录
- `/data`: 要监控的目录

## 注意事项

1. 首次运行时，应用程序会要求您授权百度网盘访问权限
2. 确保您的配置文件 `config/config.yaml` 已正确设置
3. 如果要加密上传文件，请设置 `ENCRYPT=true` 并根据需要调整 `PASSWORD`
4. 如果想要避免交互式授权流程，可以提前获取授权码并通过 `AUTH_CODE` 环境变量传入
5. 容器使用主机网络模式 (network_mode: host)，可以直接访问宿主机网络，有助于处理需要网络发现或特定端口绑定的场景
