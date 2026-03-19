"""安装依赖脚本"""
import subprocess
import sys
import os

# 清除代理环境变量
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    if key in os.environ:
        del os.environ[key]

# 设置不使用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

# 需要安装的包
packages = ['beautifulsoup4', 'cloudscraper']

# 尝试不同的镜像源
mirrors = [
    ("阿里云", "https://mirrors.aliyun.com/pypi/simple/", "mirrors.aliyun.com"),
    ("清华", "https://pypi.tuna.tsinghua.edu.cn/simple/", "pypi.tuna.tsinghua.edu.cn"),
    ("腾讯", "https://mirrors.cloud.tencent.com/pypi/simple/", "mirrors.cloud.tencent.com"),
    ("豆瓣", "http://pypi.doubanio.com/simple/", "pypi.doubanio.com"),
    ("华为", "https://repo.huaweicloud.com/repository/pypi/simple/", "repo.huaweicloud.com"),
]

for package in packages:
    print(f"\n正在安装 {package}...")
    installed = False
    
    for name, url, host in mirrors:
        print(f"尝试 {name} 镜像源...")
        try:
            cmd = [
                sys.executable, '-m', 'pip', 'install', package,
                '-i', url,
                '--trusted-host', host
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print(f"成功安装 {package}!")
                installed = True
                break
            else:
                print(f"失败: {result.stderr[:200]}")
        except Exception as e:
            print(f"异常: {e}")
    
    if not installed:
        print(f"警告: {package} 安装失败，请手动安装")

print("\n依赖安装完成!")