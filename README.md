## aioweb

``aioweb`` is a lightweight async web framework.

### Installation
You can run this code directly by downloading this repos into your desktop PC. 

To install ``aioweb`` by source code, download this repository and sequentially run following 
commands in your terminal/command line:
```commandline
python setup.py build
python setup.py install --record files.txt
```
If you want to uninstall this package, please run the following command in the same directory. 
For linux/macOS:
```commandline
xargs rm -rf < files.txt
```
For windows powershell:
```commandline
Get-Content files.txt | ForEach-Object {Remove-Item $_ -Recurse -Force}
```
You can permanently uninstall this package by **further** deleting the directory 
``../lib/python3.x/site-packages/aioweb-0.0.1.egg/``.


### How to use
The ``examples`` folder has a simple example. 
The website designed with ``aioweb`` is <a href="https://hliangzhao.cn/">hliangzhao.cn</a>.
