
NODE_TYPE = "type"
NODE_PROJECT = "project"
NODE_SERVICE = "service"
NODE_METHOD = "method"
NODE_MODULE = "module"

PARAMS = "params"
RESULT = "result"
TIMEOUT = 10
BROKER = "amqp://guest:guest@localhost"
SERVICE_INPUT = "properties"
METHOD_INPUT = "page_bed_status"
SEND_BUTTON_SEND_TEXT = "Send"
SEND_BUTTON_WAIT_TEXT = "Waiting Result..."

MAX_LENGTH = 50000   # qlabel显示太长的字符串会导致界面卡住
AMQP_URI_CONFIG_KEY = "AMQP_URI"


README = """
1. namekoman类似于postman，是为了解决使用nameko shell发送请求麻烦的问题。打开如遇权限问题，系统偏好设置->安全性与隐私->通用，点击允许。
按下右键可以添加服务，服务下可以新建模块，模块下可以添加方法，数据会存储在namekoman.json文件中
2. 将应用复制进/Applications文件夹，选中app右键选择显示包内容，进入Contents/Resources，可以编辑namekoman.json
3. rpc超时时间默认为{}s
4. 填写params时，按下cmd+r，会有惊喜
5. 代码：https://github.com/mooonpark/namekoman
""".format(TIMEOUT)
