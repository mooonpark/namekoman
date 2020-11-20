# namekoman
1. 解压namekoman.zip将namekoman放到/Applications目录下，双击打开，如遇权限问题，系统偏好设置->安全性与隐私->通用，点击允许打开
2. namekoman类似于postman，是为了解决使用nameko shell发送请求麻烦的问题，只有mac版。namekoman可以添加service，
添加method和params，点击发送按钮可以发送rpc请求。编辑过程中数据会被写进namekoman.json，保存在磁盘上
3. 在做完第一步之后，可以进入/Applications目录找到namekoman，右键选择显示包内容，进入Contents/Resources，
找到namekoman.json，可以对其进行编辑，以快速导入请求数据
4. namekoman成功发送成功请求需依赖mq，需配置broker，默认broker：amqp://guest:guest@localhost
5. rpc超时时间设置为了5s，在点击发送按钮后如果鼠标指针出现转圈，请等待5s
6. 编辑params过程中，按下cmd+r，会有惊喜
7. 新建的service和method不建议输入中文，也不应该输入中文，可能会导致程序异常（这条待定）
8. 有建议或有bug可以向我反馈
9. TODO：1) app体积太大 2) 支持一个service下新建多个同名method 3) 多个发送请求页

# 开发
Python3.6

# 打包
Pyinstaller
