# -*- coding:utf-8 -*-

import os
import sys
import json
import time
import logging
import traceback
import collections

from nameko.cli.utils.config import setup_config
from nameko.standalone.rpc import ClusterRpcClient
from PyQt5.Qt import QStandardItem, QStandardItemModel, QPoint, QCursor
from PyQt5.QtCore import Qt as QtCoreQt, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QMouseEvent
from PyQt5.Qsci import QsciScintilla, QsciLexerJSON
from PyQt5.QtWidgets import (QWidget, QTreeView, QPushButton, QLineEdit, QPlainTextEdit,
                             QLabel, QGridLayout, QApplication, QBoxLayout,
                             QInputDialog, QMessageBox, QMenu, QScrollArea
                             )

# 防止未处理的异常导致app崩溃
# import cgitb
# cgitb.enable(format="text")

CONST_TYPE = "type"
CONST_SERVICE = "service"
CONST_METHOD = "method"
CONST_MODULE = "module"
CONST_PARAMS = "params"
CONST_TIMEOUT = 10
CONST_BROKER = "amqp://guest:guest@localhost"
CONST_SERVICE_INPUT = "properties"
CONST_METHOD_INPUT = "page_bed_status"
CONST_SEND_BUTTON_SEND_TEXT = "Send"
CONST_SEND_BUTTON_WAIT_TEXT = "Waiting Result..."
MAX_LENGTH = 50000   # qlabel显示太长的字符串会导致界面卡主
AMQP_URI_CONFIG_KEY = "AMQP_URI"


def getFilePath(filepath):
    # 需要这样写，否则pyinstaller打包后会找不到文件
    return os.path.join(os.path.dirname(sys.argv[0]), filepath)


def readFile(filePath):
    with open(filePath) as f:
        return f.read()


CONST_DATA_FILE_PATH = getFilePath("namekoman.json")

README = """
1. namekoman类似于postman，是为了解决使用nameko shell发送请求麻烦的问题。打开如遇权限问题，系统偏好设置->安全性与隐私->通用，点击允许。
按下右键可以添加服务，服务下可以新建模块，模块下可以添加方法，数据会存储在namekoman.json文件中
2. 将应用复制进/Applications文件夹，选中app右键选择显示包内容，进入Contents/Resources，可以编辑namekoman.json
3. rpc超时时间默认为{}s
4. 填写params时，按下cmd+r，会有惊喜
5. 代码：https://github.com/mooonpark/namekoman
""".format(CONST_TIMEOUT)


def getAMQPConfig(broker):
    return {AMQP_URI_CONFIG_KEY: broker}


def objectToJsonStr(obj) -> str:
    return json.dumps(obj,
                      sort_keys=True,
                      indent=4,
                      separators=(", ", ": "),
                      ensure_ascii=False
                      )


def strToJsonStr(s: str) -> str:
    try:
        return objectToJsonStr(json.loads(s))
    except:
        return s.replace("'", '"').replace("：", ":")\
            .replace("“", '"').replace("”", '"').replace("，", ",")\
            .replace("【", "[").replace("】", "]")


def errorToDict(errorStr: str) -> dict:
    return dict(error=errorStr)


def errorToJsonStr(errorStr: str) -> str:
    return objectToJsonStr(errorToDict(errorStr))


def alert(text: str):
    box = QMessageBox()
    box.setText(text)
    box.show()
    box.exec_()


class QTextEditLogger(logging.Handler, QObject):
    logSignal = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__()
        QObject.__init__(self)
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.logSignal.connect(self.widget.appendPlainText)

    def emit(self, record):
        msg = self.format(record)
        self.logSignal.emit(msg)


class Storage(object):
    """
    数据存储类
    """
    def __init__(self, path):
        self.path = path
        self.data = self.loadData()

    def loadData(self):
        try:
            with open(self.path) as f:
                return collections.OrderedDict(json.loads(f.read()))
                # return collections.OrderedDict(json.loads(f.read(), object_hook=collections.OrderedDict))
        except Exception as e:
            logging.exception(e)
            return collections.OrderedDict()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(objectToJsonStr(self.data))

    def getData(self):
        return self.data

    def loggingData(self):
        logging.info("Storage data: {}".format(objectToJsonStr(self.getData())))

    def updateServiceName(self, old, new):
        if old != new:
            if new in self.data:
                return False
            if old in self.data:
                self.data[new] = self.data[old]
                del self.data[old]
                self.save()
        return True

    def updateModuleName(self, service, old, new):
        if old != new:
            try:
                if new in self.data[service]:
                    return False
                self.data[service][new] = self.data[service][old]
                del self.data[service][old]
                self.save()
            except Exception as e:
                logging.exception(e)
                return False
        return True

    def updateMethodName(self, service, module, old, new):
        if old != new:
            try:
                if new in self.data[service][module]:
                    return False
                self.data[service][module][new] = self.data[service][module][old]
                del self.data[service][module][old]
                self.save()
            except Exception as e:
                logging.exception(e)
                return False
        return True

    def updateParams(self, service, module, method, params):
        if service in self.data and module in self.data[service]:
            self.data[service][module][method] = params if isinstance(params, dict) else dict()
            self.save()

    def addService(self, service):
        if service in self.data:
            return False
        self.data[service] = dict()
        self.save()
        return True

    def addModule(self, service, module):
        if service in self.data and module in self.data[service]:
            return False
        self.data[service][module] = dict()
        self.save()
        return True

    def addMethod(self, service, module, method, params):
        if service in self.data and module in self.data[service] and method in self.data[service][module]:
            return False
        self.data[service][module][method] = params if params else dict()
        self.save()
        return True

    def getParam(self, service, module, method):
        try:
            return self.data[service][module][method]
        except Exception as e:
            logging.exception(e)
            return collections.OrderedDict()


storage = Storage(CONST_DATA_FILE_PATH)


class TreeNode(QStandardItem):
    """
    节点有两种类型
    service节点：服务，service节点service，module，method相同
    module节点：模块，一个service可以根据业务分为模块，模块的module和method相同
    method节点：方法，一个module下有对个rpc方法
    """
    def __init__(self, *args, nodeType, service, module, method, **kwargs):

        self.setType(nodeType)
        self.setServiceName(service)
        self.setModuleName(module)
        self.setMethodName(method)

        super().__init__(*args, **kwargs)

    def setType(self, nodeType):
        self.nodeType = nodeType

    def getType(self):
        return self.nodeType

    def getModuleName(self):
        return self.module

    def setModuleName(self, module):
        self.module = module

    def getServiceName(self):
        return self.service

    def setServiceName(self, service):
        self.service = service

    def getMethodName(self):
        return self.method

    def setMethodName(self, method):
        self.method = method

    def getNodeInfo(self):
        info = {
            CONST_SERVICE: self.service,
            CONST_MODULE: self.module,
            CONST_METHOD: self.method,
            CONST_PARAMS: self.getParams(),
            CONST_TYPE: self.getType()
        }
        logging.info("TreeNode info: {}".format(objectToJsonStr(info)))
        return info

    def getName(self):
        return self.getNodeInfo()[self.getType()]

    def updateName(self, name):
        if self.getType() == CONST_SERVICE:
            flag = storage.updateServiceName(self.service, name)
            if not flag:
                return False
            self.setServiceName(name)
            self.setModuleName(name)
            self.setMethodName(name)

            # 更新所有子节点service，包括module，和module的method
            index = 0
            while self.child(index):
                moduleNode = self.child(index)
                moduleNode.setServiceName(name)
                index2 = 0
                while moduleNode.child(index2):
                    methodNode = moduleNode.child(index2)
                    methodNode.setServiceName(name)
                    index2 += 1
                index += 1
        elif self.getType() == CONST_MODULE:
            flag = storage.updateModuleName(self.service, self.module, name)
            if not flag:
                return False
            self.setModuleName(name)
            self.setMethodName(name)

            # 更新所有子节点module
            index = 0
            while self.child(index):
                childNode = self.child(index)
                childNode.setModuleName(name)
                index += 1
        else:
            flag = storage.updateMethodName(self.service, self.module, self.method, name)
            if not flag:
                return False
            self.setMethodName(name)

        self.setText(name)
        self.loggingInfo()
        return True

    def updateParams(self, params):
        storage.updateParams(self.service, self.module, self.method, params)

    def getParams(self):
        if self.getType() == CONST_METHOD:
            return storage.getParam(self.service, self.module, self.method)
        else:
            return collections.OrderedDict()

    def getParent(self):
        return self.parent()

    def loggingInfo(self):
        logging.info("TreeNode type: {}, service: {}, module:{}, method: {}".format(
            self.getType(), self.getServiceName(), self.getModuleName(), self.getMethodName()
        ))


class FolderTreeView(QTreeView):

    def __init__(self):
        super().__init__()
        self.setContextMenuPolicy(QtCoreQt.CustomContextMenu)
        self.setModel(QStandardItemModel())
        self.setHeaderHidden(True)
        # self.setDragDropMode(self.InternalMove)
        # self.setDragEnabled(False)
        # self.setAcceptDrops(False)
        # self.setDropIndicatorShown(False)
        # self.setFrameStyle(QFrame.NoFrame)

    # 禁用双击事件
    def mouseDoubleClickEvent(self, e: QMouseEvent):
        pass

    # 禁用Enter按键
    def keyPressEvent(self, event):
        if event.key() != QtCoreQt.Key_Return:
            super().keyPressEvent(event)

    def addRootItem(self, item):
        self.model().invisibleRootItem().appendRow(item)

    def getNodeByPos(self, pos: QPoint) -> TreeNode:
        return self.model().itemFromIndex(self.indexAt(pos))


class FolderWidget(QWidget):

    clickNodeSingal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 400)
        self.setMaximumSize(400, 2000)
        layout = QBoxLayout(QBoxLayout.TopToBottom)
        layout.setContentsMargins(0, 0, 0, 0)  # 取消组件间间隙
        self.treeView = FolderTreeView()
        layout.addWidget(self.treeView)
        self.loadFromFile()
        self.setLayout(layout)
        self.treeView.clicked.connect(self.onTreeNodeClicked)
        self.treeView.customContextMenuRequested.connect(self.showContextMenu)

        # 鼠标选中的item
        self.clickedItem = None

    def getCurrentClickedNode(self) -> TreeNode:
        """
        获取鼠标当前点击节点
        """
        return self.treeView.model().itemFromIndex(self.treeView.currentIndex())

    def loadFromFile(self):
        """
        从文件读取数据，初始化文件夹树
        """
        data = storage.getData()
        if data:
            for service, serviceDict in data.items():
                serviceNode = self.newServiceNode(service)
                for module, moduleDict in serviceDict.items():
                    moduleNode = self.newModuleNode(service, module)
                    serviceNode.appendRow(moduleNode)
                    for method, methodDict in moduleDict.items():
                        methodNode = self.newMethodNode(service, module, method)
                        moduleNode.appendRow(methodNode)
                self.treeView.addRootItem(serviceNode)
            self.treeView.expandAll()

    def showContextMenu(self, pos: QPoint):
        self.clickedItem = self.treeView.getNodeByPos(pos)

        menu = QMenu(self)
        if self.clickedItem is None:
            action = menu.addAction("add service")
            action.triggered.connect(self.onAddService)
        elif self.clickedItem.getType() == CONST_SERVICE:
            action = menu.addAction("add module")
            action.triggered.connect(self.onAddModule)
            action = menu.addAction("add service")
            action.triggered.connect(self.onAddService)
            action = menu.addAction("rename")
            action.triggered.connect(self.onRename)
        elif self.clickedItem.getType() == CONST_MODULE:
            action = menu.addAction("add method")
            action.triggered.connect(self.onAddMethod)
            action = menu.addAction("rename")
            action.triggered.connect(self.onRename)
        else:
            action = menu.addAction("rename")
            action.triggered.connect(self.onRename)
        menu.exec_(QCursor.pos())

    def newServiceNode(self, service) -> TreeNode:
        node = TreeNode(service, nodeType=CONST_SERVICE, service=service, module=service, method=service)
        return node

    def newModuleNode(self, service, module) -> TreeNode:
        node = TreeNode(module, nodeType=CONST_MODULE, service=service, module=module, method=module)
        return node

    def newMethodNode(self, service, module, method) -> TreeNode:
        node = TreeNode(method, nodeType=CONST_METHOD, service=service, module=module, method=method)
        return node

    def onTreeNodeClicked(self, modelIndex):
        """
        根据index找到鼠标点击的节点，发送节点数据到其他控件，用于显示
        """
        node = self.treeView.model().itemFromIndex(modelIndex)
        self.clickNodeSingal.emit(node.getNodeInfo())

    def onAddService(self):
        name, ok = QInputDialog.getText(self, "⌨️", "Please enter service name")
        if ok:
            if name == "":
                alert("Service name is empty!")
                return
            if not storage.addService(name):
                alert("Input has one, please change one!")
                return
            node = self.newServiceNode(name)
            self.treeView.addRootItem(node)

    def onAddModule(self):
        name, ok = QInputDialog.getText(self, "⌨️", "Please enter module name")
        if ok:
            if name == "":
                alert("Module name is empty!")
                return
            service = self.clickedItem.getName()
            if not storage.addModule(service, name):
                alert("Input has one, please change one!")
                return
            node = self.newModuleNode(service, name)
            self.clickedItem.appendRow(node)

    def onAddMethod(self):
        name, ok = QInputDialog.getText(self, "⌨️", "Please enter method name")
        if ok:
            if name == "":
                alert("Method name is empty!")
                return
            service = self.clickedItem.getParent().getName()
            module = self.clickedItem.getName()

            if not storage.addMethod(service, module, name, None):
                alert("Input has one, please change one!")
                return

            node = self.newMethodNode(service, module, name)
            self.clickedItem.appendRow(node)

    def onRename(self):
        msg = "Please enter new name"
        name, ok = QInputDialog().getText(self, "⌨️", msg, text=self.clickedItem.getName())
        if ok:
            if name == "":
                alert("Input is empty!")
                return

            if not self.clickedItem.updateName(name):
                alert("Input has one, please change one!")
                return
            info = {
                CONST_SERVICE: self.clickedItem.getServiceName(),
                CONST_METHOD: name,
                CONST_PARAMS: None
            }
            self.clickNodeSingal.emit(info)


class NamekoManQsciScintilla(QsciScintilla):

    def __init__(self):
        super().__init__()

    def keyPressEvent(self, event):
        """
        监听cmd + r 按键事件
        """
        if event.modifiers() == QtCoreQt.ControlModifier and event.key() == QtCoreQt.Key_R:
            self.setText(strToJsonStr(self.text()))
        else:
            super().keyPressEvent(event)


class SendRpcThread(QThread):
    """
    发送rpc用线程处理，防止阻塞主线程
    """
    finishSignal = pyqtSignal(str)

    def __init__(self, client: ClusterRpcClient, service: str, method: str, params: dict):
        self.client, self.service, self.method, self.params = client, service, method, params
        super().__init__()

    def run(self):
        start = time.time()
        logging.info("Send rpc start, service: {}, method: {}, params: {}, waiting result......".format(
            self.service, self.method, self.params
        ))
        try:
            result = getattr(getattr(self.client, self.service), self.method)(**self.params)
        except Exception as e:
            result = errorToDict(repr(e))
            logging.exception(e)

        end = time.time()
        result = objectToJsonStr(result)
        logging.info("Send rpc end, calling time: {}, service: {}, method: {}, params:{}, result: {}".format(
            end-start, self.service, self.method, objectToJsonStr(self.params), result
        ))
        self.finishSignal.emit(result)


class NamekoManWidget(QWidget):
    RPC = "rpc"

    def __init__(self):
        super().__init__()
        self.broker = CONST_BROKER
        self.brokerEdit = QLineEdit(self.broker)
        self.brokerEdit.setPlaceholderText("Input mq broker, for example: {}".format(CONST_BROKER))
        self.timeout = CONST_TIMEOUT
        self.timeoutEdit = QLineEdit(str(self.timeout))
        self.timeoutEdit.setPlaceholderText("Input timeout")
        self.timeoutEdit.setMaximumWidth(100)
        self.sendButton = QPushButton(CONST_SEND_BUTTON_SEND_TEXT)
        self.serviceEdit = QLineEdit()
        self.serviceEdit.setFocusPolicy(QtCoreQt.NoFocus)
        self.serviceEdit.setPlaceholderText("Input service name, for example: {}".format(CONST_SERVICE_INPUT))
        self.methodEdit = QLineEdit()
        self.methodEdit.setFocusPolicy(QtCoreQt.NoFocus)
        self.methodEdit.setMinimumWidth(400)
        self.methodEdit.setPlaceholderText("Input method name, for example: {}".format(CONST_METHOD_INPUT))

        # 初始化输出日志组件
        self.logTextBox = QTextEditLogger(self)
        self.logTextBox.widget.setMinimumHeight(150)
        self.logTextBox.widget.setMaximumHeight(300)
        self.logTextBox.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self.logTextBox)
        logging.getLogger().setLevel(logging.DEBUG)

        # 初始化代码编辑控件
        lexer = QsciLexerJSON()
        lexer.setHighlightComments(False)
        lexer.setHighlightEscapeSequences(False)
        self.paramsEdit = NamekoManQsciScintilla()
        self.paramsEdit.setLexer(lexer)
        self.paramsEdit.setUtf8(True)
        self.paramsEdit.setMarginLineNumbers(0, True)
        self.paramsEdit.setAutoIndent(True)
        self.paramsEdit.setTabWidth(4)
        self.paramsEdit.setFolding(QsciScintilla.BoxedTreeFoldStyle)
        self.paramsEdit.setFoldMarginColors(QtCoreQt.gray, QtCoreQt.lightGray)
        self.paramsEdit.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.paramsEdit.setIndentationGuides(QsciScintilla.SC_IV_LOOKBOTH)

        # 初始化结果显示控件，支持滚动
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.resultLabel = QLabel("")
        self.resultLabel.setAlignment(QtCoreQt.AlignCenter)
        self.resultLabel.adjustSize()
        self.resultLabel.setWordWrap(True)
        self.resultLabel.setAlignment(QtCoreQt.AlignLeft)
        self.resultLabel.setTextInteractionFlags(QtCoreQt.TextSelectableByMouse)
        self.resultLabel.setText(README)
        self.scrollArea.setWidget(self.resultLabel)
        self.scrollArea.setMinimumSize(500, 600)

        # 初始化文件夹树
        self.folderBar = FolderWidget()

        # 使用网格布局进行布局
        self.layout = QGridLayout()
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.addWidget(self.folderBar, 0, 0, 25, 1)
        self.layout.addWidget(self.brokerEdit, 0, 1, 1, 1)
        self.layout.addWidget(self.timeoutEdit, 0, 2, 1, 1)
        self.layout.addWidget(self.serviceEdit, 1, 1, 1, 2)
        self.layout.addWidget(self.methodEdit, 2, 1, 1, 2)
        self.layout.addWidget(self.paramsEdit, 3, 1, 22, 2)
        self.layout.addWidget(self.sendButton, 0, 3, 1, 1)
        self.layout.addWidget(self.scrollArea, 1, 3, 24, 1)
        self.layout.addWidget(self.logTextBox.widget, 25, 0, 1, 4)
        self.setLayout(self.layout)

        self.sendButton.clicked.connect(self.onSendRpc)
        self.folderBar.clickNodeSingal.connect(self.onClickedNode)

        # 初始化nameko client
        self.initNameko()

        self.rpcThread = None

    def showResult(self, result: str):
        # 为了显示居中，用2个空格替换1个空格
        self.resultLabel.setText(result.replace(" ", "  "))
        self.resultLabel.repaint()

    def getBrokerInput(self):
        return self.brokerEdit.text()

    def getTimeoutInput(self):
        timeout = self.timeoutEdit.text()
        try:
            return int(timeout)
        except Exception as e:
            logging.exception(e)
            return CONST_TIMEOUT

    def hasNamekoClient(self):
        return hasattr(self, self.RPC)

    def setNamekoClient(self):
        """
        更新配置，再设置一个新的rpc客户端
        """
        setup_config(None, define=getAMQPConfig(self.broker))
        client = ClusterRpcClient(timeout=self.getTimeoutInput())
        setattr(self, self.RPC, client.start())
        logging.info("Set new nameko, broker:{}, timeout:{}".format(
            self.getBrokerInput(), self.getTimeoutInput())
        )

    def initNameko(self):
        """
        如果没有构建好rpc客户端，新建一个，如果已经构建好删除再使用新的配置新建
        """
        broker = self.getBrokerInput()
        timeout = self.getTimeoutInput()
        try:
            if not self.hasNamekoClient():
                self.broker = broker
                self.setNamekoClient()
            else:
                if broker != self.broker or timeout != self.timeout:
                    self.broker = broker
                    self.timeout = timeout
                    delattr(self, self.RPC)
                    self.setNamekoClient()
        except Exception as e:
            self.showResult(errorToJsonStr(repr(e)))
            logging.exception(e)

    def lockSendButton(self):
        self.sendButton.setDisabled(True)
        self.sendButton.setText(CONST_SEND_BUTTON_WAIT_TEXT)
        self.sendButton.repaint()

    def unlockSendButton(self):
        self.sendButton.setDisabled(False)
        self.sendButton.setText(CONST_SEND_BUTTON_SEND_TEXT)
        self.sendButton.repaint()

    def onClickedNode(self, info):
        """
        显示鼠标选择节点数据
        """
        self.serviceEdit.setText(info.get(CONST_SERVICE, ""))
        self.methodEdit.setText(info.get(CONST_METHOD, ""))
        params = info.get(CONST_PARAMS, {})
        if params is not None:
            self.paramsEdit.setText(objectToJsonStr(params))

    def onSendRpc(self):
        self.initNameko()

        if not self.hasNamekoClient():
            self.showResult(errorToJsonStr("Can't connect to mq, please check mq or broker!"))
            return
        node = self.folderBar.getCurrentClickedNode()
        if not node or node.getType() != CONST_METHOD:
            alert("Please choose one method!")
            return
        service, method, params = self.serviceEdit.text(), self.methodEdit.text(), self.paramsEdit.text()

        try:
            params = json.loads(params)
            self.lockSendButton()
            self.rpcThread = SendRpcThread(getattr(self, self.RPC), service, method, params)
            self.rpcThread.finishSignal.connect(self.onSendRpcFinished)
            self.rpcThread.start()
        except Exception as e:
            self.showResult(errorToJsonStr(repr(e)))

        node.updateParams(params)

    def onSendRpcFinished(self, result: str):
        if len(result) > MAX_LENGTH:
            result = result[:MAX_LENGTH]
            result += "...... Sorry, the result is too long. Please check the log for whole result."
        self.showResult(result)
        self.unlockSendButton()


def error_handler(etype, value, tb):
    msg = "".join(traceback.format_exception(etype, value, tb))
    logging.error("Unknow exception: {}".format(msg))


if __name__ == "__main__":
    sys.excepthook = error_handler

    app = QApplication([])
    widget = NamekoManWidget()
    widget.resize(1200, 800)
    widget.setMaximumSize(5000, 2500)
    widget.show()
    sys.exit(app.exec_())
