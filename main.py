import yaml
import os
import sys
import time
import argparse
from datetime import datetime
import threading
import queue
import requests
from modules import auth
from modules.upload_new import encrypt_upload, auto_chunked_upload_optimized

# 尝试导入pyinotify，如果不存在则提示安装
try:
    import pyinotify
except ImportError:
    print("请先安装pyinotify库: pip install pyinotify")
    sys.exit(1)

def get_config() -> dict:
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)
    return config

def get_access_token(config: dict, auth_code: str = None) -> str:
    if auth_code is None:
        auth_code = auth.get_code(config)
    refresh_token = auth.oauthtoken_authorizationcode(config, auth_code)
    access_token, refresh_token= auth.oauthtoken_refreshtoken(config, refresh_token)
    print("Access Token:", access_token)
    
    # 计算过期时间戳（当前时间 + 2582000秒，约30天）
    current_time = int(time.time())
    expire_in = current_time + 2582000
    
    config['AccessToken'] = access_token
    config['RefreshToken'] = refresh_token
    config['ExpireIn'] = expire_in
    
    print(f"Token 将在 {datetime.fromtimestamp(expire_in).strftime('%Y-%m-%d %H:%M:%S')} 过期")
    
    with open('config/config.yaml', 'w') as f:
        yaml.safe_dump(config, f)
    return access_token

def refresh_access_token(config: dict) -> str:
    refresh_token = config.get('RefreshToken')
    if not refresh_token:
        raise ValueError("Refresh token not found in configuration.")
    access_token, refresh_token = auth.oauthtoken_refreshtoken(config, refresh_token)
    print("Refreshed Access Token:", access_token)
    print("Refreshed Refresh Token:", refresh_token)
    
    # 计算过期时间戳（当前时间 + 2582000秒，约30天）
    current_time = int(time.time())
    expire_in = current_time + 2582000
    
    config['AccessToken'] = access_token
    config['RefreshToken'] = refresh_token
    config['ExpireIn'] = expire_in
    
    print(f"Token 将在 {datetime.fromtimestamp(expire_in).strftime('%Y-%m-%d %H:%M:%S')} 过期")
    
    with open('config/config.yaml', 'w') as f:
        yaml.safe_dump(config, f)
    return access_token

# 文件上传队列
upload_queue = queue.Queue()

class UploadWorker(threading.Thread):
    """处理上传队列的工作线程"""
    
    def __init__(self, access_token, remote_base_dir, encrypt=False, password="123456", worker_id=0):
        super().__init__(daemon=True)
        self.access_token = access_token
        self.remote_base_dir = remote_base_dir
        self.encrypt = encrypt
        self.password = password
        self.running = True
        self.worker_id = worker_id
    
    def run(self):
        while self.running:
            try:
                # 从队列获取文件，如果5秒内没有新文件则继续检查running状态
                try:
                    # 获取文件路径和基础目录
                    file_info = upload_queue.get(timeout=5)
                    if isinstance(file_info, tuple) and len(file_info) == 2:
                        file_path, base_dir = file_info
                    else:
                        file_path, base_dir = file_info, None
                except queue.Empty:
                    continue
                
                # 构建远程路径，保持相对路径结构
                if base_dir:
                    # 获取相对路径
                    rel_path = os.path.relpath(file_path, base_dir)
                    # 构建远程路径，保持相对路径结构
                    remote_path = os.path.join(self.remote_base_dir, rel_path).replace('\\', '/')
                else:
                    # 如果没有提供基础目录，只使用文件名（兼容旧版本）
                    file_name = os.path.basename(file_path)
                    remote_path = os.path.join(self.remote_base_dir, file_name).replace('\\', '/')
                
                # 确保远程路径以/开头
                if not remote_path.startswith('/'):
                    remote_path = '/' + remote_path
                
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{current_time}] 线程-{self.worker_id} 开始上传文件: {file_path} -> {remote_path}")
                
                # 执行上传（加密或普通）
                if self.encrypt:
                    result = encrypt_upload(
                        access_token=self.access_token,
                        local_file_path=file_path,
                        remote_path=remote_path,
                        password=self.password
                    )
                else:
                    result = auto_chunked_upload_optimized(
                        access_token=self.access_token,
                        local_file_path=file_path,
                        remote_path=remote_path
                    )
                
                # 标记任务完成
                upload_queue.task_done()
                
                # 获取文件名用于输出
                file_name = os.path.basename(file_path)
                
                # 输出上传结果
                if result:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 线程-{self.worker_id} 上传成功: {file_name}")
                else:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ 线程-{self.worker_id} 上传失败: {file_name}")
                
            except Exception as e:
                print(f"线程-{self.worker_id} 上传过程中出错: {str(e)}  {file_path}")
                input()
                # 标记任务完成，避免队列阻塞
                try:
                    upload_queue.task_done()
                except:
                    pass
    
    def stop(self):
        self.running = False

class FileMonitor:
    """监控目录文件变化的类，使用inotify机制"""
    
    def __init__(self, watch_dir, recursive=True, file_types=None, min_size=0, 
                 cooldown=2, exclude_patterns=None, exclude_dirs=None, config=None, upload_workers=None):
        """
        初始化文件监控器
        
        Args:
            watch_dir (str): 要监控的目录
            recursive (bool): 是否递归监控子目录
            file_types (list): 要监控的文件类型列表，如['.jpg', '.pdf']，None表示所有类型
            min_size (int): 最小文件大小(字节)，小于此大小的文件不会触发上传
            cooldown (int): 文件冷却时间(秒)，新文件创建后等待此时间再上传，避免上传未完成的文件
            exclude_patterns (list): 要排除的文件名模式列表，支持通配符
            exclude_dirs (list): 要排除的目录名称或路径列表
            config (dict): 配置字典，用于刷新令牌
            upload_workers (list): 上传工作线程列表，用于更新令牌
        """
        self.watch_dir = os.path.abspath(watch_dir)
        self.recursive = recursive
        self.file_types = file_types
        self.min_size = min_size
        self.cooldown = cooldown
        self.exclude_patterns = exclude_patterns or []
        self.exclude_dirs = exclude_dirs or []
        self.pending_files = {}  # 待处理文件字典 {文件路径: 首次检测时间}
        self.config = config
        self.upload_workers = upload_workers
        self.last_token_check = time.time()  # 上次检查令牌的时间
        
        # 确保监控目录存在
        if not os.path.exists(self.watch_dir):
            raise FileNotFoundError(f"监控目录不存在: {self.watch_dir}")
        
        # 创建watch manager
        self.wm = pyinotify.WatchManager()
        # 监控文件创建和修改事件
        self.mask = pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE
    
    def _is_excluded(self, file_path):
        """检查文件是否应该被排除"""
        import fnmatch
        file_name = os.path.basename(file_path)
        file_dir = os.path.dirname(file_path)
        
        # 检查文件类型
        if self.file_types and not any(file_name.endswith(ext) for ext in self.file_types):
            return True
        
        # 检查排除模式
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return True
        
        # 检查排除目录
        for exclude_dir in self.exclude_dirs:
            # 检查是否为绝对路径
            if os.path.isabs(exclude_dir):
                # 如果文件位于排除目录下
                if file_dir.startswith(exclude_dir):
                    return True
            else:
                # 如果是相对目录名，检查文件的父目录名或路径中是否包含该目录
                dir_components = file_dir.split(os.path.sep)
                if exclude_dir in dir_components:
                    return True
                
                # 还需要检查相对于监控目录的路径
                rel_path = os.path.relpath(file_dir, self.watch_dir)
                rel_components = rel_path.split(os.path.sep)
                if exclude_dir in rel_components:
                    return True
        
        return False
    
    def _process_pending_files(self):
        """处理待上传的文件"""
        current_time = time.time()
        files_to_remove = []
        
        # 检查访问令牌是否过期，每小时检查一次
        if self.config and self.upload_workers and current_time - self.last_token_check > 3600:
            self.last_token_check = current_time
            if is_token_expired(self.config):
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 访问令牌已过期或即将过期，正在刷新...")
                try:
                    new_token = refresh_access_token(self.config)
                    # 更新所有上传工作线程的访问令牌
                    for worker in self.upload_workers:
                        worker.access_token = new_token
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 访问令牌已刷新")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 刷新访问令牌失败: {e}")
        
        for file_path, detected_time in list(self.pending_files.items()):
            # 检查文件是否已存在足够长时间
            if current_time - detected_time >= self.cooldown:
                # 检查文件是否仍然存在
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    # 检查文件大小
                    file_size = os.path.getsize(file_path)
                    if file_size >= self.min_size:
                        # 将文件添加到上传队列，同时传递监控目录路径
                        upload_queue.put((file_path, self.watch_dir))
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 将文件加入上传队列: {file_path}")
                
                # 从待处理列表中移除
                files_to_remove.append(file_path)
        
        # 移除已处理的文件
        for file_path in files_to_remove:
            self.pending_files.pop(file_path, None)
    
    def start_monitoring(self):
        """开始监控文件系统事件"""
        # 创建事件处理器
        handler = FileEventHandler(self)
        
        # 创建通知器
        notifier = pyinotify.Notifier(self.wm, handler)
        
        # 添加要监控的目录
        if self.recursive:
            self.wm.add_watch(self.watch_dir, self.mask, rec=True, auto_add=True)
        else:
            self.wm.add_watch(self.watch_dir, self.mask)
        
        # 输出开始监控的提示
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始监控目录: {self.watch_dir}" + 
              (" (包含子目录)" if self.recursive else ""))
        print("按 Ctrl+C 停止监控")
        print("-" * 60)
        
        # 启动处理线程
        processor_thread = threading.Thread(target=self._pending_file_processor, daemon=True)
        processor_thread.start()
        
        try:
            # 开始监控循环
            notifier.loop()
        except KeyboardInterrupt:
            print("\n监控已停止")
        finally:
            # 确保资源被正确释放
            notifier.stop()
    
    def _pending_file_processor(self):
        """后台线程，定期处理待上传文件"""
        while True:
            self._process_pending_files()
            time.sleep(1)  # 每秒检查一次

class FileEventHandler(pyinotify.ProcessEvent):
    """处理inotify事件的类"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        super().__init__()
    
    def process_IN_CREATE(self, event):
        """处理文件创建事件"""
        # 忽略目录创建事件
        if event.dir:
            return
        
        self._handle_file_event(event.pathname)
    
    def process_IN_CLOSE_WRITE(self, event):
        """处理文件写入完成事件"""
        # 忽略目录
        if event.dir:
            return
        
        self._handle_file_event(event.pathname)
    
    def _handle_file_event(self, file_path):
        """处理文件事件的通用方法"""
        # 如果文件应该被排除，则忽略
        if self.monitor._is_excluded(file_path):
            return
        
        # 如果文件不在待处理列表中，添加它
        if file_path not in self.monitor.pending_files:
            current_time = time.time()
            self.monitor.pending_files[file_path] = current_time
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检测到新文件: {file_path}")

def scan_and_upload_existing_files(watch_dir, recursive=True, file_types=None, min_size=0, exclude_patterns=None, exclude_dirs=None):
    """
    扫描目录中已存在的文件并添加到上传队列
    
    Args:
        watch_dir (str): 要扫描的目录
        recursive (bool): 是否递归扫描子目录
        file_types (list): 要处理的文件类型列表，如['.jpg', '.pdf']，None表示所有类型
        min_size (int): 最小文件大小(字节)，小于此大小的文件不会上传
        exclude_patterns (list): 要排除的文件名模式列表，支持通配符
        exclude_dirs (list): 要排除的目录名称或路径列表
        
    Returns:
        int: 添加到上传队列的文件数量
    """
    import fnmatch
    
    def is_excluded(file_path):
        """检查文件是否应该被排除"""
        file_name = os.path.basename(file_path)
        file_dir = os.path.dirname(file_path)
        
        # 检查文件类型
        if file_types and not any(file_name.endswith(ext) for ext in file_types):
            return True
        
        # 检查排除模式
        for pattern in exclude_patterns or []:
            if fnmatch.fnmatch(file_name, pattern):
                return True
        
        # 检查排除目录
        for exclude_dir in exclude_dirs or []:
            # 检查是否为绝对路径
            if os.path.isabs(exclude_dir):
                # 如果文件位于排除目录下
                if file_dir.startswith(exclude_dir):
                    return True
            else:
                # 如果是相对目录名，检查文件的父目录名或路径中是否包含该目录
                dir_components = file_dir.split(os.path.sep)
                if exclude_dir in dir_components:
                    return True
                
                # 还需要检查相对于监控目录的路径
                rel_path = os.path.relpath(file_dir, watch_dir)
                rel_components = rel_path.split(os.path.sep)
                if exclude_dir in rel_components:
                    return True
        
        return False
    
    count = 0
    watch_dir = os.path.abspath(watch_dir)
    
    # 遍历目录
    for root, dirs, files in os.walk(watch_dir):
        # 如果不递归且不是根目录，跳过
        if not recursive and root != watch_dir:
            continue
        
        # 根据排除目录列表从当前搜索中排除目录
        if exclude_dirs:
            # 使用副本进行修改，避免影响原始 dirs 列表
            dirs_to_remove = []
            for d in dirs:
                dir_path = os.path.join(root, d)
                
                # 检查是否为排除目录
                for exclude_dir in exclude_dirs:
                    # 如果是绝对路径
                    if os.path.isabs(exclude_dir) and dir_path.startswith(exclude_dir):
                        dirs_to_remove.append(d)
                        break
                    
                    # 如果是相对路径
                    rel_path = os.path.relpath(dir_path, watch_dir)
                    rel_components = rel_path.split(os.path.sep)
                    
                    if exclude_dir in rel_components or d == exclude_dir:
                        dirs_to_remove.append(d)
                        break
            
            # 从搜索列表中移除排除目录
            for d in dirs_to_remove:
                dirs.remove(d)
            
        for file_name in files:
            file_path = os.path.join(root, file_name)
            
            # 检查排除规则
            if is_excluded(file_path):
                continue
                
            # 检查文件大小
            try:
                file_size = os.path.getsize(file_path)
                if file_size < min_size:
                    continue
            except (OSError, IOError):
                continue
                
            # 添加到上传队列
            upload_queue.put((file_path, watch_dir))
            count += 1
            
        # 如果不递归，只处理顶级目录后就退出
        if not recursive:
            break
            
    return count

def if_accesstoken_valid(access_token) -> bool:
    url = f"https://pan.baidu.com/rest/2.0/xpan/nas?access_token={access_token}&method=uinfo&vip_version=v2"
    payload = {}
    try:
        response = requests.request("GET", url, data=payload)
        result = response.json()
        print(result)
        return result.get('errmsg') == 'succ'
    except Exception as e:
        print(f"验证访问令牌时出错: {e}")
        return False

def is_token_expired(config) -> bool:
    """检查令牌是否已过期或即将过期"""
    expire_in = config.get('ExpireIn')
    if not expire_in:
        return True  # 如果没有过期时间，则视为已过期
    
    current_time = int(time.time())
    # 如果当前时间已经超过过期时间，或者即将在一天内过期
    if current_time >= expire_in - 86400:  # 86400秒 = 1天
        print(f"令牌已过期或即将过期。过期时间: {datetime.fromtimestamp(expire_in).strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    
    return False
if __name__ == '__main__':
    debug = True
    parser = argparse.ArgumentParser(description="百度网盘文件自动加密上传工具")

    if debug:
        parser.add_argument("-d", "--directory",
                        help="要监控的目录路径",default="./")
    else:
        parser.add_argument("-d", "--directory", required=True,
                        help="要监控的目录路径")
    parser.add_argument("-r", "--remote-dir", default="/apps/autoSync",
                        help="百度网盘中的目标目录，默认为/apps/autoSync")
    parser.add_argument("-e", "--encrypt", action="store_true",
                        help="是否加密上传文件",default=False)
    parser.add_argument("-p", "--password", default="123456",
                        help="加密密码，默认为123456")
    parser.add_argument("-n", "--no-recursive", action="store_true",
                        help="不递归监控子目录")
    parser.add_argument("-t", "--file-types", 
                        help="要监控的文件类型，逗号分隔，如'.jpg,.png,.pdf'")
    parser.add_argument("-s", "--min-size", type=int, default=0,
                        help="最小文件大小(字节)，小于此大小的文件不会上传")
    parser.add_argument("-c", "--cooldown", type=int, default=2,
                        help="文件冷却时间(秒)，新文件创建后等待此时间再上传")
    parser.add_argument("-x", "--exclude", 
                        help="要排除的文件名模式，逗号分隔，如'*.tmp,~*'")
    parser.add_argument("-X", "--exclude-dirs",
                        help="要排除的目录名称或路径，逗号分隔，如'tmp,cache,.git'")
    parser.add_argument("-u", "--upload-existing", action="store_true",
                        help="是否上传监控目录中已存在的文件",default=False)
    parser.add_argument("-w", "--workers", type=int, default=3,
                        help="上传工作线程数，默认为3")
    parser.add_argument("--auth-code",
                        help="授权码，用于获取访问令牌")
    
    args = parser.parse_args()
    
    # 处理文件类型参数
    file_types = None
    if args.file_types:
        file_types = [t.strip() for t in args.file_types.split(',')]
    
    # 处理排除模式参数
    exclude_patterns = []
    if args.exclude:
        exclude_patterns = [p.strip() for p in args.exclude.split(',')]
    
    # 处理排除目录参数
    exclude_dirs = []
    if args.exclude_dirs:
        exclude_dirs = [d.strip() for d in args.exclude_dirs.split(',')]
    
    try:
        # 获取配置和访问令牌
        config = get_config()
        access_token = None
        if args.auth_code:
            print("使用提供的授权码获取访问令牌...")
            access_token = get_access_token(config, args.auth_code)
        # 检查配置中是否有必要的令牌信息
        elif config.get('RefreshToken') is None:
            print("当前配置不包含 RefreshToken，尝试获取新的访问令牌...")
            access_token = get_access_token(config, args.auth_code)
        elif config.get('AccessToken') is None:
            print("当前配置中没有 AccessToken，尝试使用 RefreshToken 刷新...")
            access_token = refresh_access_token(config)
        else:
            # 先检查令牌是否过期
            if is_token_expired(config):
                print("访问令牌已过期或即将过期，尝试刷新...")
                access_token = refresh_access_token(config)
            else:
                access_token = config.get('AccessToken')
                expire_time = datetime.fromtimestamp(config.get('ExpireIn')).strftime('%Y-%m-%d %H:%M:%S')
                print(f"使用现有访问令牌，将在 {expire_time} 过期")
                
        # 验证访问令牌是否有效
        if access_token and not if_accesstoken_valid(access_token):
            print("访问令牌无效，尝试重新获取...")
            access_token = get_access_token(config, args.auth_code)
            
        
        # 创建多个上传工作线程
        upload_workers = []
        num_workers = max(1, args.workers)  # 至少创建1个线程
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 创建 {num_workers} 个上传工作线程")
        
        for i in range(num_workers):
            worker = UploadWorker(
                access_token=access_token,
                remote_base_dir=args.remote_dir,
                encrypt=args.encrypt,
                password=args.password,
                worker_id=i+1
            )
            worker.start()
            upload_workers.append(worker)
        
        # 创建文件监控器
        monitor = FileMonitor(
            watch_dir=args.directory,
            recursive=not args.no_recursive,
            file_types=file_types,
            min_size=args.min_size,
            cooldown=args.cooldown,
            exclude_patterns=exclude_patterns,
            exclude_dirs=exclude_dirs,
            config=config,
            upload_workers=upload_workers
        )
        
        # 如果指定了上传现有文件
        if args.upload_existing:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始扫描并上传已存在的文件...")
            uploaded_count = scan_and_upload_existing_files(
                watch_dir=args.directory,
                recursive=not args.no_recursive,
                file_types=file_types,
                min_size=args.min_size,
                exclude_patterns=exclude_patterns,
                exclude_dirs=exclude_dirs
            )
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 已添加 {uploaded_count} 个现有文件到上传队列")
        
        # 启动文件监控
        monitor.start_monitoring()
        
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)