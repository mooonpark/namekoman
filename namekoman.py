# -*- coding:utf-8 -*-

import os
import sys
import json
import logging
import traceback
import collections

from nameko.cli.utils.config import setup_config
from nameko.standalone.rpc import ClusterRpcClient
from PyQt5.Qt import QStandardItem, QStandardItemModel, QPoint, QCursor
from PyQt5.QtCore import Qt as QtCoreQt

from PyQt5.QtGui import QMouseEvent
from PyQt5.Qsci import QsciScintilla, QsciLexerJSON
from PyQt5.QtWidgets import (QWidget, QTreeView, QPushButton, QLineEdit, QPlainTextEdit,
                             QLabel, QGridLayout, QApplication, QBoxLayout,
                             QInputDialog, QMessageBox, QMenu, QScrollArea
                             )

# 防止未处理的异常导致app崩溃
# import cgitb
# cgitb.enable(format="text")

CONST_IS_DIR = "isDir"
CONST_SERVICE = "service"
CONST_METHOD = "method"
CONST_PARAMS = "params"
CONST_BROKER = "amqp://guest:guest@localhost"
CONST_SERVICE_INPUT = "properties"
CONST_METHOD_INPUT = "page_bed_status"

AMQP_URI_CONFIG_KEY = "AMQP_URI"

README = """
1. 解压namekoman.zip将namekoman放到/Applications目录下，双击打开，如遇权限问题，系统偏好设置->安全性与隐私->通用，点击允许打开
2. namekoman类似于postman，是为了解决使用nameko shell发送请求麻烦的问题，只有mac版。namekoman可以添加service，
添加method和params，点击发送按钮可以发送rpc请求。编辑过程中数据会被写进namekoman.json，保存在磁盘上。
3. 在做完第一步之后，可以进入/Applications目录找到namekoman，右键选择显示包内容，进入Contents/Resources，
找到namekoman.json，可以对其进行编辑，以快速导入请求数据
4. namekoman成功发送成功请求需依赖mq，需配置broker，默认broker：amqp://guest:guest@localhost
5. rpc超时时间设置为了5s，在点击发送按钮后如果鼠标指针出现转圈，请等待5s
6. 编辑params过程中，按下cmd+r，会有惊喜
7. 代码地址：https://github.com/Liusple/namekoman.git
8. 新建的service和method不建议输入中文，也不应该输入中文，可能会导致程序异常（这条待定）
9. 有建议或有bug可以向我反馈
10.TODO：
    1）app体积太大
    2）支持一个service下新建多个同名method
    3）多个发送请求页
11. 感谢
"""


def getFilePath(filepath):
    return os.path.join(os.path.dirname(sys.argv[0]), filepath)


# 需要这样写，否则pyinstaller打包后会找不到文件
CONST_DATA_FILE_PATH = getFilePath("namekoman.json")
# CONST_FOLDER_PATH = getFilePath("icons8-folder.svg")
# CONST_FILE_PATH = getFilePath("icons8-file.svg")


def getAMQPConfig(broker):
    # nameko mq配置key使用的AMQP_URI_CONFIG_KEY
    return {AMQP_URI_CONFIG_KEY: broker}


def dictToJsonStr(dataDict):
    return json.dumps(dataDict, sort_keys=True, indent=4, separators=(", ", ": "), ensure_ascii=False)


def strToJsonStr(dictStr):
    try:
        return dictToJsonStr(json.loads(dictStr))
    except:
        return dictStr


def errorToJsonStr(error):
    return dictToJsonStr(dict(error=error))


def alert(text: str):
    box = QMessageBox()
    box.setText(text)
    box.show()
    box.exec_()


class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)


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
        except Exception as e:
            logging.exception(e)
            return collections.OrderedDict()

    def save(self):
        with open(self.path, "w") as f:
            f.write(dictToJsonStr(self.data))

    def getData(self):
        return self.data

    def updateServiceName(self, old, new):
        if old != new:
            if new in self.data:
                return False
            if old in self.data:
                self.data[new] = self.data[old]
                del self.data[old]
            self.save()
        return True

    def updateMethodName(self, service, old, new):
        if old != new:
            serviceDict = self.data.get(service)
            if serviceDict and new in serviceDict:
                return False
            if serviceDict and old in serviceDict:
                self.data[service][new] = serviceDict[old]
                del self.data[service][old]
            self.save()
        return True

    def addService(self, service):
        if service not in self.data:
            self.data[service] = dict()
            self.save()

    def addMethod(self, service, method, params):
        if service in self.data:
            self.data[service][method] = params if params else dict()
            self.save()

    def getParam(self, service, method):
        try:
            return self.data[service][method]
        except Exception as e:
            logging.exception(e)
            return collections.OrderedDict()


STORAGE = Storage(CONST_DATA_FILE_PATH)


class TreeNode(QStandardItem):
    """
    节点有两种类型，ISDIR Ture表示service，False表示method
    service节点：service和method相同
    method节点：service表示服务名，method表示方法名
    """
    def __init__(self, *args, **kwargs):
        if CONST_IS_DIR in kwargs:
            self.setIsDir(kwargs[CONST_IS_DIR])
            del kwargs[CONST_IS_DIR]
        else:
            self.setIsDir(False)

        if CONST_SERVICE in kwargs:
            self.setServiceName(kwargs[CONST_SERVICE])
            del kwargs[CONST_SERVICE]
        else:
            self.setServiceName("")

        if CONST_METHOD in kwargs:
            self.setMethodName(kwargs[CONST_METHOD])
            del kwargs[CONST_METHOD]
        else:
            self.setMethodName("")

        # if CONST_PARAMS in kwargs:
        #     self.params = kwargs[CONST_PARAMS]
        #     del kwargs[CONST_PARAMS]
        # else:
        #     self.params = ""

        super().__init__(*args, **kwargs)

    def setIsDir(self, isDir):
        self.isDir = isDir

    def checkIsDir(self):
        return self.isDir

    def getServiceName(self):
        return self.service

    def setServiceName(self, service):
        self.service = service

    def getMethodName(self):
        return self.method

    def setMethodName(self, method):
        self.method = method

    def getName(self):
        if self.checkIsDir():
            return self.service
        return self.method

    def updateName(self, name):

        if self.checkIsDir():
            flag = STORAGE.updateServiceName(self.service, name)
            if not flag:
                return False
            self.setServiceName(name)
            self.setMethodName(name)

            # 更新所有子节点service
            index = 0
            while self.child(index):
                childNode = self.child(index)
                childNode.setServiceName(name)
                index += 1
        else:
            flag = STORAGE.updateMethodName(self.service, self.method, name)
            if not flag:
                return False
            self.setMethodName(name)

        self.setText(name)
        return True

    def getRpcInfo(self):
        params = STORAGE.getParam(self.service, self.method)
        return {
            CONST_SERVICE: self.service,
            CONST_METHOD: self.method,
            CONST_PARAMS: params,
        }


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
        # self.folderIcon = QIcon(CONST_FOLDER_PATH)
        # self.fileIcon = QIcon(CONST_FILE_PATH)

    # 禁用双击事件
    def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:
        pass

    def addRootItem(self, item):
        self.model().invisibleRootItem().appendRow(item)

    def getNodeByPos(self, pos: QPoint) -> TreeNode:
        return self.model().itemFromIndex(self.indexAt(pos))


class FolderBar(QWidget):

    # 传入三个edit控件是不是不好，是不是应该用信号进行文本的更新？
    def __init__(self, serviceEdit, methodEdit, paramsEdit):
        super().__init__()
        self.setMinimumSize(300, 400)
        self.setMaximumSize(400, 2000)
        layout = QBoxLayout(QBoxLayout.TopToBottom)
        # 取消组件间间隙
        layout.setContentsMargins(0, 0, 0, 0)
        self.treeView = FolderTreeView()
        layout.addWidget(self.treeView)
        self.loadFromFile()
        self.setLayout(layout)
        self.treeView.clicked.connect(self.onTreeNodeClicked)
        self.treeView.customContextMenuRequested.connect(self.showContextMenu)

        # 鼠标点击的item
        self.clickedItem = None
        self.serviceEdit = serviceEdit
        self.methodEdit = methodEdit
        self.paramsEdit = paramsEdit

    def loadFromFile(self):
        data = STORAGE.getData()
        if data:
            for service, serviceDict in data.items():
                node = self.newServiceNode(service)
                for method, params in serviceDict.items():
                    self.addItem(node, name=method, isDir=False, service=service, method=method)
                self.treeView.addRootItem(node)
            self.treeView.expandAll()

    def addItem(self, parent: QStandardItem, name: str, isDir: bool, **kwargs) -> TreeNode:
        node = TreeNode(name, **kwargs)
        if not isDir:
            node.setDropEnabled(False)
            # node.setIcon(self.treeView.fileIcon)
        # else:
        #     node.setIcon(self.treeView.folderIcon)

        node.setText(name)
        parent.appendRow(node)
        return node

    def showContextMenu(self, pos: QPoint):
        self.clickedItem = self.treeView.getNodeByPos(pos)

        menu = QMenu(self)
        if self.clickedItem is None:
            action = menu.addAction("add service")
            action.triggered.connect(self.onAddService)
        if self.clickedItem is not None:
            if self.clickedItem.checkIsDir():
                action = menu.addAction("add method")
                action.triggered.connect(self.onAddMethod)
            action = menu.addAction("rename")
            action.triggered.connect(self.onRename)

        menu.exec_(QCursor.pos())

    def newServiceNode(self, service: str) -> TreeNode:
        node = TreeNode(service, service=service, method=service, isDir=True)
        # node.setIcon(self.treeView.folderIcon)
        return node

    def newMethodNode(self, service, method: str) -> TreeNode:
        node = TreeNode(method, service=service, method=method, isDir=False)
        # node.setIcon(self.treeView.fileIcon)
        return node

    def onTreeNodeClicked(self, modelIndex):
        # 从文件里获取最新的数据，因为有时更新了params保存到了文件但是没有同步到qtreeview
        node = self.treeView.model().itemFromIndex(modelIndex)
        info = node.getRpcInfo()
        service = info.get(CONST_SERVICE, "")
        method = info.get(CONST_METHOD, "")
        params = info.get(CONST_PARAMS, {})
        self.showInfo(service, method, dictToJsonStr(params))

    def showInfo(self, service, method, params):
        self.serviceEdit.setText(service)
        self.methodEdit.setText(method)
        if params:
            self.paramsEdit.setText(params)

    def onAddService(self):
        name, ok = QInputDialog.getText(self, "⌨️", "Please enter service name")
        if ok:
            if name == "":
                alert("Service name is empty!")
                return
            node = self.newServiceNode(name)
            if self.clickedItem is None:
                self.treeView.addRootItem(node)

            STORAGE.addService(name)

    def onAddMethod(self):
        name, ok = QInputDialog.getText(self, "⌨️", "Please enter method name")
        if ok:
            if name == "":
                alert("Method name is empty!")
                return
            service = self.clickedItem.getName()
            node = self.newMethodNode(service, name)
            if self.clickedItem.checkIsDir():
                self.clickedItem.appendRow(node)
            STORAGE.addMethod(service, name, None)

    def onRename(self):
        msg = "Please enter service name" if self.clickedItem.checkIsDir() else "Please enter method name"
        name, ok = QInputDialog().getText(self, "⌨️", msg, text=self.clickedItem.getName())
        if ok:
            if name == "":
                alert("Input is empty!")
                return

            if not self.clickedItem.updateName(name):
                alert("Input has one, please change one!")
                return
            STORAGE.save()
            self.showInfo(self.clickedItem.getServiceName(), name, None)


class NamekoManQsciScintilla(QsciScintilla):
    def __init__(self):
        super().__init__()

    def keyPressEvent(self, event):
        # 监听cmd + r 按键事件
        if event.modifiers() == QtCoreQt.ControlModifier and event.key() == QtCoreQt.Key_R:
            self.setText(strToJsonStr(self.text()))
        else:
            super().keyPressEvent(event)


class NamekoManWidget(QWidget):
    RPC = "rpc"

    def __init__(self):
        super().__init__()

        self.sendButton = QPushButton("Send")
        self.serviceEdit = QLineEdit()
        self.serviceEdit.setPlaceholderText("Input service name, for example: {}".format(CONST_SERVICE_INPUT))
        self.methodEdit = QLineEdit()
        self.methodEdit.setMinimumWidth(400)
        self.methodEdit.setPlaceholderText("Input method name, for example: {}".format(CONST_METHOD_INPUT))
        self.brokerEdit = QLineEdit()
        self.broker = CONST_BROKER
        self.brokerEdit.setPlaceholderText("Input mq broker, for example: {}".format(CONST_BROKER))
        self.brokerEdit.setText(CONST_BROKER)
        self.logTextBox = QTextEditLogger(self)
        self.logTextBox.widget.setMinimumHeight(150)
        self.logTextBox.widget.setMaximumHeight(250)
        self.logTextBox.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self.logTextBox)
        logging.getLogger().setLevel(logging.DEBUG)

        # 初始化代码编辑控件
        lexer = QsciLexerJSON()
        # lexer.setHighlightComments(False)
        # lexer.setHighlightEscapeSequences(False)
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

        self.serviceLabel = QLabel(CONST_SERVICE)
        self.methodLabel = QLabel(CONST_METHOD)
        self.paramsLabel = QLabel(CONST_PARAMS)
        self.folderBar = FolderBar(self.serviceEdit, self.methodEdit, self.paramsEdit)

        # 使用网格布局
        self.layout = QGridLayout()
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.addWidget(self.folderBar, 0, 0, 25, 1)
        self.layout.addWidget(self.brokerEdit, 0, 1, 1, 1)
        self.layout.addWidget(self.serviceEdit, 1, 1, 1, 1)
        self.layout.addWidget(self.methodEdit, 2, 1, 1, 1)
        self.layout.addWidget(self.paramsEdit, 3, 1, 22, 1)
        self.layout.addWidget(self.sendButton, 0, 2, 1, 1)
        self.layout.addWidget(self.scrollArea, 1, 2, 24, 1)
        self.layout.addWidget(self.logTextBox.widget, 25, 0, 1, 3)
        self.setLayout(self.layout)

        self.sendButton.clicked.connect(self.onSendRpc)

        self.initNameko()

    def setNameko(self):
        # 更新配置，再初始化一个新的rpc客户端
        setup_config(None, define=getAMQPConfig(self.broker))
        client = ClusterRpcClient(timeout=5)
        setattr(self, self.RPC, client.start())

    def initNameko(self):
        brokerEdit = self.brokerEdit.text()
        try:
            if not hasattr(self, self.RPC):
                self.broker = brokerEdit
                self.setNameko()
            else:
                # 删除旧的rpc客户端，新建一个新的客户端
                if brokerEdit != self.broker:
                    self.broker = brokerEdit
                    delattr(self, self.RPC)
                    self.setNameko()
        except Exception as e:
            logging.exception(e)
            self.showResult(errorToJsonStr(repr(e)))

    def showResult(self, result):
        self.resultLabel.setText(result)
        self.resultLabel.repaint()

    def onSendRpc(self):
        self.initNameko()

        if not hasattr(self, self.RPC):
            self.showResult(errorToJsonStr("Can't connect to mq, please check mq or broker!"))
            return

        service = self.serviceEdit.text()
        method = self.methodEdit.text()
        logging.info("Send rpc start, waiting result......")
        try:
            params = json.loads(self.paramsEdit.text())
            result = getattr(getattr(getattr(self, self.RPC), service), method)(**params)
        except Exception as e:
            logging.exception(e)
            self.showResult(errorToJsonStr(repr(e)))
            return
        result = dictToJsonStr(result)
        self.showResult(result)
        STORAGE.addMethod(service, method, params)
        logging.info("Send rpc end:\n{}".format(result))


def error_handler(etype, value, tb):
    msg = "".join(traceback.format_exception(etype, value, tb))
    logging.info("Unknow exception: {}".format(msg))


if __name__ == "__main__":
    sys.excepthook = error_handler
    app = QApplication([])
    widget = NamekoManWidget()
    widget.resize(1100, 800)
    widget.setMaximumSize(5000, 2500)
    widget.show()
    sys.exit(app.exec_())
