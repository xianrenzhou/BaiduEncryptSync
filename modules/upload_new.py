# !/usr/bin/env python3
"""
    xpan upload
    include:
        precreate
        upload
        create
        auto_chunked_upload (自动分片上传)
        encrypt_upload (加密上传)
"""
import os
import sys
import hashlib
import json
import io
import concurrent.futures
import threading
import time
import tempfile
from tqdm import tqdm

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(BASE_DIR)
from pprint import pprint
from openapi_client.api import fileupload_api
import openapi_client

# 导入加密工具
try:
    from modules.crypto_utils import encrypt_data, decrypt_data, encrypt_file, decrypt_file
except ImportError:
    print("警告: 加密模块导入失败，加密功能将不可用")
    print("请安装所需依赖: pip install pycryptodome")
    
    # 提供空的加密函数以避免导入错误
    def encrypt_data(data, password="123456"):
        return data
        
    def decrypt_data(data, password="123456"):
        return data
        
    def encrypt_file(input_file_path, output_file_path=None, password="123456"):
        return input_file_path
        
    def decrypt_file(input_file_path, output_file_path=None, password="123456"):
        return input_file_path



def calculate_file_md5(file_path):
    """计算整个文件的MD5"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def split_file_to_chunks(file_path, chunk_size=4*1024*1024, encrypt=False, password="123456"):
    """
    将文件分片并计算每个分片的MD5
    
    Args:
        file_path (str): 文件路径
        chunk_size (int): 分片大小，默认4MB
        encrypt (bool): 是否加密文件内容
        password (str): 加密密码，默认为123456
        
    Returns:
        tuple: (chunks_info, total_size)
            chunks_info: list of dict with keys: 'data', 'md5', 'size', 'index'
            total_size: 文件总大小
    """
    chunks_info = []
    total_size = 0
    
    # 检查文件是否为空
    if os.path.getsize(file_path) == 0:
        # 对于空文件，创建一个空的块信息
        empty_md5 = hashlib.md5(b"").hexdigest()
        chunks_info.append({
            'data': b"",
            'md5': empty_md5,
            'size': 0,
            'index': 0
        })
        return chunks_info, 0
    
    # 如果需要加密，先将整个文件加密后再分片
    if encrypt:
        try:
            # 创建临时文件用于存储加密数据
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
            
            # 加密文件内容
            with open(file_path, 'rb') as f:
                file_data = f.read()
                
            encrypted_data = encrypt_data(file_data, password)
            
            with open(temp_path, 'wb') as f:
                f.write(encrypted_data)
                
            # 使用加密后的文件进行后续处理
            file_to_process = temp_path
        except Exception as e:
            print(f"加密文件失败: {e}")
            # 如果加密失败，使用原始文件
            file_to_process = file_path
    else:
        file_to_process = file_path
    
    with open(file_to_process, 'rb') as f:
        chunk_index = 0
        while True:
            chunk_data = f.read(chunk_size)
            if not chunk_data:
                break
                
            # 计算分片MD5
            chunk_md5 = hashlib.md5(chunk_data).hexdigest()
            
            chunks_info.append({
                'data': chunk_data,
                'md5': chunk_md5,
                'size': len(chunk_data),
                'index': chunk_index
            })
            
            total_size += len(chunk_data)
            chunk_index += 1
    
    # 如果创建了临时文件，删除它
    if encrypt and 'temp_path' in locals():
        try:
            os.unlink(temp_path)
        except:
            pass
    
    return chunks_info, total_size


class TqdmUploadTracker:
    """
    基于tqdm的上传进度监控类
    """
    _lock = threading.Lock()
    
    def __init__(self, total_chunks, file_name, total_size):
        self.total_chunks = total_chunks
        self.file_name = file_name
        self.total_size = total_size
        self.uploaded_bytes = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        # 创建tqdm进度条实例
        self.pbar = tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            desc=f"⬆️  {file_name}",
            bar_format="{desc}: {percentage:3.1f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
    
    def update(self, chunk_size):
        """更新上传进度"""
        with self.lock:
            self.uploaded_bytes += chunk_size
            self.pbar.update(chunk_size)
    
    def close(self, success=True, duration=None):
        """关闭进度条"""
        with self.lock:
            self.pbar.close()
            
            # 显示完成状态
            if success and duration:
                speed = (self.uploaded_bytes / duration) / (1024 * 1024) if duration > 0 else 0
                # print(f"✅ {self.file_name} 上传完成 | {speed:.2f} MB/s")
            else:
                print(f"❌ {self.file_name} 上传失败")


def auto_chunked_upload(access_token, local_file_path, remote_path, rtype=3, max_workers=3, chunk_size=4*1024*1024, 
                   show_progress=True, encrypt=False, password="123456"):
    """
    自动分片上传文件到百度网盘（支持并发上传）
    
    Args:
        access_token (str): 访问令牌
        local_file_path (str): 本地文件路径
        remote_path (str): 远程文件路径，如 "/apps/your-app-name/filename.txt"
        rtype (int): 返回类型，默认为3
        max_workers (int): 最大并发线程数，默认为3
        chunk_size (int): 分片大小，默认4MB
        show_progress (bool): 是否显示进度，默认为True
        encrypt (bool): 是否加密文件内容
        password (str): 加密密码，默认为123456
        
    Returns:
        dict: 上传结果
    """
    
    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"本地文件不存在: {local_file_path}")
    
    # 获取文件信息并分片
    chunks_info, total_size = split_file_to_chunks(local_file_path, chunk_size, encrypt, password)
    
    file_name = os.path.basename(local_file_path)
    
    # 如果加密了，文件名添加.enc后缀以标识（仅在显示时，不影响实际上传路径）
    display_name = file_name
    if encrypt:
        display_name = file_name + " [已加密]"
    
    # 构造block_list (MD5列表)
    block_list = [chunk['md5'] for chunk in chunks_info]
    block_list_json = json.dumps(block_list)
    
    # 创建进度监控器（如果需要并且文件大小不为0）
    progress_tracker = None
    if show_progress and total_size > 0:
        progress_tracker = TqdmUploadTracker(len(chunks_info), display_name, total_size)
    elif show_progress:
        print(f"⬆️  上传空文件: {display_name}")
    
    # 创建API客户端
    with openapi_client.ApiClient() as api_client:
        api_instance = fileupload_api.FileuploadApi(api_client)
        
        # 1. 预上传 - 获取uploadid
        start_time = time.time()
        try:
            precreate_response = api_instance.xpanfileprecreate(
                access_token=access_token,
                path=remote_path,
                isdir=0,  # 0表示文件，1表示目录
                size=total_size,
                autoinit=1,
                block_list=block_list_json,
                rtype=rtype
            )
            
            # 从响应中获取uploadid
            uploadid = precreate_response.get('uploadid')
            if not uploadid:
                if total_size > 0:  # 只有非空文件才详细输出错误
                    print(f"预上传失败，未获取到uploadid，请检查路径或文件大小: {remote_path}")
                    print(f"文件大小: {total_size} 字节")
                    print(f"分块列表: {block_list}")
                    print(f"预上传响应: {precreate_response}")
                else:
                    print(f"空文件预上传失败: {remote_path}")
                    print(f"预上传响应: {precreate_response}")
                raise Exception("预上传失败：未获取到uploadid")
                
        except openapi_client.ApiException as e:
            if show_progress and progress_tracker:
                progress_tracker.close(False)
            return None
        
        # 2. 并发分片上传
        upload_start_time = time.time()
        
        # 如果是空文件，跳过分片上传步骤
        if total_size == 0:
            if show_progress:
                print(f"⬆️  跳过空文件分片上传: {display_name}")
        else:
            def upload_chunk(chunk_info):
                """上传单个分片的函数"""
                chunk_index = chunk_info['index']
                chunk_data = chunk_info['data']
                
                try:
                    # 创建新的API客户端实例（线程安全）
                    with openapi_client.ApiClient() as thread_api_client:
                        thread_api_instance = fileupload_api.FileuploadApi(thread_api_client)
                        
                        # 使用 BytesIO 创建文件对象
                        chunk_file = io.BytesIO(chunk_data)
                        chunk_file.seek(0)
                        # 添加 name 属性，避免 AttributeError
                        chunk_file.name = f"chunk_{chunk_index}.tmp"
                        
                        # 上传分片
                        upload_response = thread_api_instance.pcssuperfile2(
                            access_token=access_token,
                            partseq=str(chunk_index),  # 分片序号
                            path=remote_path,
                            uploadid=uploadid,
                            type="tmpfile",
                            file=chunk_file
                        )
                        
                        # 关闭文件对象
                        chunk_file.close()
                        
                        # 更新上传进度（如果启用）
                        if progress_tracker:
                            progress_tracker.update(len(chunk_data))
                        
                        return chunk_index, upload_response
                        
                except Exception as e:
                    if show_progress:
                        print(f"\n❌ {file_name} 分片 {chunk_index + 1} 上传失败")
                    return chunk_index, None
            
            # 使用线程池并发上传
            upload_results = {}
            failed_chunks = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有上传任务
                future_to_chunk = {executor.submit(upload_chunk, chunk): chunk for chunk in chunks_info}
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_chunk):
                    chunk_index, result = future.result()
                    if result is not None:
                        upload_results[chunk_index] = result
                    else:
                        failed_chunks.append(chunk_index)
            
            upload_end_time = time.time()
            upload_duration = upload_end_time - upload_start_time
            
            # 关闭进度条
            if progress_tracker:
                progress_tracker.close(len(failed_chunks) == 0, upload_duration)
            
            # 检查是否有失败的分片
            if failed_chunks:
                if show_progress:
                    print(f"❌ {file_name} 有 {len(failed_chunks)} 个分片上传失败")
                return None
        
        # 3. 文件合并
        try:
            create_response = api_instance.xpanfilecreate(
                access_token=access_token,
                path=remote_path,
                isdir=0,
                size=total_size,
                uploadid=uploadid,
                block_list=block_list_json,
                rtype=rtype
            )
            
            # 输出完成信息
            if show_progress:
                if total_size == 0:
                    print(f"✅ 空文件 {file_name} 上传完成")
                else:
                    end_time = time.time()
                    total_duration = end_time - start_time
                    print(f"✅ {file_name} 上传完成，总耗时: {total_duration:.2f}秒")
            
            return create_response
            
        except openapi_client.ApiException as e:
            if show_progress:
                print(f"❌ {file_name} 文件合并失败")
            return None


def encrypt_upload(access_token, local_file_path, remote_path, password="123456", rtype=3, show_progress=True):
    """
    加密上传文件到百度网盘
    
    Args:
        access_token (str): 访问令牌
        local_file_path (str): 本地文件路径
        remote_path (str): 远程文件路径
        password (str): 加密密码，默认为123456
        rtype (int): 返回类型，默认为3
        show_progress (bool): 是否显示进度，默认为True
        
    Returns:
        dict: 上传结果，包含额外的元数据用于解密
    """
    # 调用加密上传函数
    result = auto_chunked_upload_optimized(
        access_token=access_token,
        local_file_path=local_file_path,
        remote_path=remote_path,
        rtype=rtype,
        show_progress=show_progress,
        encrypt=True,
        password=password
    )
    
    # 如果上传成功，显示加密信息
    if result and show_progress:
        file_name = os.path.basename(local_file_path)
        print(f"✅ {file_name} 已加密上传，请保存好密钥以便日后解密")
    
    return result


def auto_chunked_upload_optimized(access_token, local_file_path, remote_path, rtype=3, show_progress=True, 
                            encrypt=False, password="123456"):
    """
    优化版本的自动分片上传（自动调整参数）
    
    Args:
        access_token (str): 访问令牌
        local_file_path (str): 本地文件路径
        remote_path (str): 远程文件路径
        rtype (int): 返回类型，默认为3
        show_progress (bool): 是否显示进度，默认为True
        encrypt (bool): 是否加密文件内容
        password (str): 加密密码，默认为123456
        
    Returns:
        dict: 上传结果
    """
    file_size = os.path.getsize(local_file_path)
    file_name = os.path.basename(local_file_path)

    chunk_size = 4 * 1024 * 1024  # 4MB分片
    max_workers = 3

    # 添加加密标识到返回的元数据中，以便于后续解密
    metadata = {
        "encrypted": encrypt,
        "original_file": file_name
    }
    
    result = auto_chunked_upload(
        access_token=access_token,
        local_file_path=local_file_path,
        remote_path=remote_path,
        rtype=rtype,
        max_workers=max_workers,
        chunk_size=chunk_size,
        show_progress=show_progress,
        encrypt=encrypt,
        password=password
    )
    
    # 如果上传成功，添加元数据
    if result and encrypt:
        result['_metadata'] = metadata
    
    return result


if __name__ == '__main__':
    # 原有的测试函数
    # precreate()
    # upload()
    # create()
    
    # 多线程并行上传多个文件
    access_token = "121.fc8ded3c2a565f9b8a287ce39b504567.YQPO1MV1hZIRGEEAW_IQjdN6oRVOR7kOCi69-ke.jHAOsQ"
    
    # 定义要上传的文件列表，包括普通上传和加密上传
    files_to_upload = [
        {
            "local_path": "./atest.txt",
            "remote_path": "/apps/apitest/atest.txt",
            "encrypt": True
        }
    ]
    
    # 定义上传结果存储字典
    upload_results = {}
    
    # 创建线程锁，用于安全更新结果字典
    results_lock = threading.Lock()
    
    def upload_file_thread(file_info):
        """线程函数：上传单个文件并保存结果"""
        local_path = file_info["local_path"]
        remote_path = file_info["remote_path"]
        encrypt = file_info.get("encrypt", False)
        password = file_info.get("password", "123456")
        
        # 根据是否加密选择上传方式
        if encrypt:
            result = encrypt_upload(
                access_token=access_token,
                local_file_path=local_path,
                remote_path=remote_path,
                password=password,
                show_progress=True
            )
        else:
            result = auto_chunked_upload_optimized(
                access_token=access_token,
                local_file_path=local_path,
                remote_path=remote_path,
                show_progress=True
            )
        
        # 安全地更新结果字典
        with results_lock:
            file_name = os.path.basename(local_path)
            upload_results[file_name] = {
                "result": result,
                "encrypted": encrypt,
                "password": password if encrypt else None
            }
    
    # 创建并启动多个上传线程
    upload_threads = []
    for file_info in files_to_upload:
        thread = threading.Thread(
            target=upload_file_thread,
            args=(file_info,)
        )
        upload_threads.append(thread)
        thread.start()
    
    # 等待所有上传线程完成
    for thread in upload_threads:
        thread.join()
    
    # 显示所有上传结果
    print("\n===== 上传结果汇总 =====")
    for file_name, info in upload_results.items():
        result = info["result"]
        encrypted = info["encrypted"]
        password = info["password"]
        
        print(f"\n文件: {file_name} {'[已加密]' if encrypted else ''}")
        if result:
            print("✅ 上传成功!")
            print(f"  文件ID: {result.get('fs_id', '未知')}")
            print(f"  文件路径: {result.get('path', '未知')}")
            print(f"  文件大小: {result.get('size', '未知')} 字节")
            print(f"  文件MD5: {result.get('md5', '未知')}")
            if encrypted:
                print(f"  加密状态: 已加密")
                print(f"  解密密钥: {password}")
        else:
            print("❌ 上传失败，请检查日志获取详细错误信息。")
