# namekoman
## Introduce
1. Namekoman is similar to postman, to solve the problem of sending requests unfriendly using nameko shell.
Right click to add a service, create a new module under the service, add methods under the module,
and will store the data in the namekoman.json and on disk
2. Unzip namekoman.zip and put it in /Application directory, double click to open it. If there is a permission
problem, system preferences->security and privacy->general, click allow to open it
3. After completing the previous step, you can enter the /Application director to find namekoman, and right click
to select show package, then enter Contents/Resources.You will find namekoman.json, you can edit it
4. Namekoman successfully sends the request depends on rabbit mq. Please config broker, default broker: amqp://guest:guest@localhost
5. Rpc timeout defaults to 10s. If the mouse pointer turns around after clicking the send button, please wait some seconds.
6. In the process of editing params, there will be a surprise if you can press cmd+r

## Requirements
- Python3.6
- PyQt5
- nameko
- pyinstaller

## Pyinstaller
### Generate spec file
pyinstaller -D -y -w namekoman.py
### Modify spec file
- Analysis
1. datas: specify the files that need to be packaged into app
2. hiddenimports: specify additional dependent packages

- BUNDLE
1. icon: specify the app icon
2. info_plist: app info

### Make app
pyinstaller -D -y namekoman.spec


# namekoman
## 介绍
1. namekoman类似于postman，是为了解决使用nameko shell发送请求麻烦的问题。
按右键可以添加服务，服务下可以新建模块，模块下可以添加方法，数据会存储在namekoman.json文件中，保存在磁盘上
2. 解压namekoman.zip将namekoman放到/Applications目录下，双击打开，如遇权限问题，系统偏好设置->安全性与隐私->通用，点击允许打开
3. 在做完上一步之后，可以进入/Applications目录找到namekoman，右键选择显示包内容，进入Contents/Resources，
找到namekoman.json，可以对其进行编辑，以快速导入请求数据
4. namekoman成功发送成功请求需依赖mq，本地请启动mq，之后需配置broker，默认broker：amqp://guest:guest@localhost
5. rpc超时时间默认为10s，在点击发送按钮后如果鼠标指针出现转圈，请等待
6. 编辑params过程中，按下cmd+r，会有惊喜
7. 新建的service和method不建议输入中文，也不应该输入中文，可能会导致程序异常（这条待定）
8. 有建议或有bug可以向我反馈
9. TODO：1) app体积太大 2) 如果返回结果非常非常多，页面也会卡住
10. 感谢
## 依赖
- Python3.6
- PyQt5
- nameko
- pyinstaller

## 打包
### 生成spec文件
pyinstaller -D -y -w namekoman.py

### 修改spec文件

#### Analysis
##### datas指定需要打包进app的文件，hiddenimports指定额外依赖的包
- BUNDLE：icon指定图标，info_plist说明程序信息，可以按照git仓库的文件进行配置
### 生成app
pyinstaller -D -y namekoman.spec


