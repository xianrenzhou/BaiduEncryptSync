# Baidu Encrypt Sync - 百度网盘加密同步工具
https://club.fnnas.com/forum.php?mod=viewthread&tid=33898&extra=

**苦苦等待飞牛加密增量备份大半年，我决定不等了！**直接手搓一个百度网盘增量加密备份的小软件。

程序借助百度网盘api官方文档实现，目前实现了基本功能。

软件已经开源：https://github.com/xianrenzhou/BaiduEncryptSync

欢迎点点star！

下面是飞牛系统部署的简易教程。

## STEP 0 代码下载

 下载代码并点上star😄，放到飞牛任意文件夹里。我这边是一个例子。

![image.png](data/attachment/forum/202508/10/225611cgghgxhmm2gkgwe2.png "image.png")



## STEP 1 基础信息设置


1. 访问 [百度网盘开放平台](https://pan.baidu.com/union/) 并登录您的百度账号。
2. 点击右上角控制台进入应用创建页面。
3. 创建应用，应用类别为软件，其余任写

   ![image.png](data/attachment/forum/202508/10/230152q16w1jo7jnjn7jnj.png "image.png")
4. 创建成功后，进入应用详情页面，获取您的 `AppKey`、`SecretKey` 和 `SignKey`，在飞牛代码路径中的config/config.yml中填写配置文件（记得加空格）。
   ![image.png](data/attachment/forum/202508/10/230305wi3mgelmmmzmme2u.png "image.png")

   ## STEP 2 docker-compose配置

   编辑docker-compose文件：

   主要改动有几个:

   WATCH_DIR: 改为你要上传的文件路径

   REMOTE_DIR: 百度网盘中目标目录，注意要以/apps/开头，比如/apps/fnos

   ENCRYPT: 加密上传开关

   PASSWORD: 加密上传密码

   UPLOAD_EXISTING:是否上传文件夹中原来的文件，如果否那就只上传以后新加入的文件。

   AUTH_CODE(非常重要):


   ```
   在浏览器中访问以下URL（请将 `你的AppKey` 替换为您的真实 AppKey），并完成授权：
   https://openapi.baidu.com/oauth/2.0/authorize?response_type=code&client_id=你的AppKey&redirect_uri=oob&scope=basic,netdisk&device_id=你的AppID

   ```

AUTH_CODE 如果没在配置文件中指定，就要去docker的终端里输入。

最终配置样例：

![image.png](data/attachment/forum/202508/10/231545jsxlly24v39cly5m.png "image.png")

### 所有环境变量表：

![image.png](data/attachment/forum/202508/10/230725m4yj7epj1j08jj70.png "image.png")


## STEP 2 运行

打开飞牛docker

选择docker-compose

选择代码所在目录，记住一定要选择main.py在的目录

运行！

![image.png](data/attachment/forum/202508/10/231909cqa1isqjoba2o22q.png "image.png")



## 检查

docker编译完成运行后，可以从docker的日志 或者查看百度网盘你设置的备份目录查看文件是否上传。

注意，文件加密参考群晖的cloudsync,没有对文件名加密，方便寻找文件。

![image.png](data/attachment/forum/202508/10/232622w50cwgqwxlmwq0oo.png "image.png")

## 解密

解密代码:https://github.com/xianrenzhou/BaiduDencrypy

请安装uv并使用uv sync同步环境后运行main.py