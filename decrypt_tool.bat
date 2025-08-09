@echo off
REM 百度网盘加密文件解密工具 - Windows批处理脚本
REM 此脚本简化了解密工具的使用，适用于Windows用户

echo ================================================
echo        百度网盘加密文件解密工具 - 快速启动
echo ================================================
echo.

REM 检查Python是否已安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未检测到Python！请先安装Python 3.6或更高版本。
    echo 您可以从 https://www.python.org/downloads/ 下载Python
    echo.
    pause
    exit /b 1
)

REM 检查依赖项是否已安装
python -c "import Crypto" >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装必要的依赖库...
    pip install pycryptodome tqdm
    if %errorlevel% neq 0 (
        echo 安装依赖失败，请手动运行: pip install pycryptodome tqdm
        pause
        exit /b 1
    )
)

echo 请选择解密模式：
echo 1. 解密单个文件
echo 2. 解密整个文件夹（不包含子文件夹）
echo 3. 解密整个文件夹及其所有子文件夹
echo.

set /p choice=请输入选项 (1/2/3): 

if "%choice%"=="1" (
    REM 解密单个文件
    echo.
    set /p file_path=请输入要解密的文件路径: 
    set /p password=请输入解密密码 (默认为123456，直接回车使用默认密码): 
    
    if "%password%"=="" set password=123456
    
    echo.
    echo 正在解密文件...
    python decrypt_files.py -f "%file_path%" -p "%password%"
) else if "%choice%"=="2" (
    REM 解密整个文件夹（不递归）
    echo.
    set /p dir_path=请输入要解密的文件夹路径: 
    set /p password=请输入解密密码 (默认为123456，直接回车使用默认密码): 
    
    if "%password%"=="" set password=123456
    
    echo.
    echo 是否保留原始加密文件？
    set /p keep=请选择 (y/n，默认n): 
    
    if /i "%keep%"=="y" (
        echo 正在解密文件夹中的文件 (保留原始文件)...
        python decrypt_files.py -d "%dir_path%" -p "%password%" -k
    ) else (
        echo 正在解密文件夹中的文件...
        python decrypt_files.py -d "%dir_path%" -p "%password%"
    )
) else if "%choice%"=="3" (
    REM 解密整个文件夹（递归）
    echo.
    set /p dir_path=请输入要解密的文件夹路径: 
    set /p password=请输入解密密码 (默认为123456，直接回车使用默认密码): 
    
    if "%password%"=="" set password=123456
    
    echo.
    echo 是否保留原始加密文件？
    set /p keep=请选择 (y/n，默认n): 
    
    if /i "%keep%"=="y" (
        echo 正在递归解密文件夹及其子文件夹中的文件 (保留原始文件)...
        python decrypt_files.py -d "%dir_path%" -p "%password%" -r -k
    ) else (
        echo 正在递归解密文件夹及其子文件夹中的文件...
        python decrypt_files.py -d "%dir_path%" -p "%password%" -r
    )
) else (
    echo 无效的选项！
    pause
    exit /b 1
)

echo.
echo 操作完成！
pause
