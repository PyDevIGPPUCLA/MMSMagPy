import os
from os.path import expanduser
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtGui import QLabel, QDial
from PyQt4.QtGui import QMainWindow
from PyQt4.QtGui import QPainter, QPen


class RangeQDial(QDial):

    def __init__(self, minimum=0, maximum=23, name=None):
        QDial.__init__(self)
        self.title = name
        self.setMinimum(minimum)
        self.setMaximum(maximum)
        self.setProperty("value", minimum)
        self.setNotchTarget(3.)
        self.setObjectName(name)
        self.setNotchesVisible(True)

    def paintEvent(self, event):
        QDial.paintEvent(self, event)
        painter = QPainter(self)
        rect = self.geometry()
        x = rect.width() / 3
        y = rect.height() / 2
        painter.setPen(QPen(QtCore.Qt.red))
        value = self.value()
        title = "{:2d}".format(value) + self.title
        painter.drawText(QtCore.QPoint(x, y), title)


class DragFromWidget(QtGui.QLineEdit):

    def __init__(self, name="EMPTY", parent=None, readOnly=True):
        super(DragFromWidget, self).__init__(parent=parent)
        self.readOnly = readOnly
        self.name = name
        self.setText(name)
        self.setReadOnly(readOnly)
        self.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum))
        if readOnly:
            p = self.palette()
            p.setColor(self.backgroundRole(), QtCore.Qt.gray)
            self.setPalette(p)

    def dragEnterEvent(self, event):
        pass
#       print("dragEnterEvent")

    def mousePressEvent(self, event):
        hotSpot = event.pos()
        mimeData = QtCore.QMimeData()
        mimeData.setText(self.text())
        mimeData.setData("application/x-hotspot", str(hotSpot.x()))
        pixmap = QtGui.QPixmap(self.size())
        self.render(pixmap)
        mimeData.setImageData(pixmap)

        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        drag.setPixmap(pixmap)
        drag.setHotSpot(hotSpot)
#       dropAction = drag.exec_(QtCore.Qt.CopyAction|QtCore.Qt.MoveAction, QtCore.Qt.CopyAction)
#       if dropAction == QtCore.Qt.MoveAction:
#           label.close()


class DragToWidget(QtGui.QFrame):

    def __init__(self, actions=None, default=None, parent=None):
        super(DragToWidget, self).__init__(parent)
        self.setFrameStyle(3)
        self.setWindowTitle("DRAG WIDGET")
#       p = self.palette()
#       p.setColor(self.backgroundRole(), QtCore.Qt.yellow)
#       self.setPalette(p)
        self.default = default
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)
        self.layout = QtGui.QBoxLayout(QtGui.QBoxLayout.LeftToRight, self)
        self.widget = QtGui.QLineEdit()
        self.widget.setReadOnly(True)
        self.layout.addWidget(self.widget)
        self.labels = []
        self.actions = actions

    def clear(self):
        self.labels = []
        self.widget.setText("")
        if self.actions:
            self.actions(self.labels)

    def reset(self):
        if self.default:
            self.labels = self.default
            self.widget.setText(self.labels)
            if self.actions:
                self.actions(self.labels)

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        text = event.mimeData().text()
        self.labels.append(text)
        self.widget.setText(str(self.labels))
        if self.actions:
            self.actions(self.labels)

    def labels(self):
        return self.labels


class FormatDialog(QtGui.QDialog):
    DICT = {"phrase": "mms", "year": "YY", "month": "MM", "day": "DD", "hour": "HH"}

    def __init__(self, setData=None, parent=None):
        super(QtGui.QDialog, self).__init__(parent)
        self._phraseList = ["mms", "year", "month", "day", "hour"]
        self.defaultList = ["mms", "year", "month", "day", "hour"]
        self.setWindowTitle("File Name Format")
        self._setData = setData
        self.setMinimumWidth(300)
        mainLayOut = QtGui.QGridLayout(self)
        widget = QtGui.QWidget()
        mainLayOut.addWidget(widget)
        widgetLayOut = QtGui.QHBoxLayout(widget)
        phrase = DragFromWidget(FormatDialog.DICT["phrase"], readOnly=False)
        year = DragFromWidget("year")
        month = DragFromWidget("month")
        day = DragFromWidget("day")
        hour = DragFromWidget("hour")
        widgetLayOut.addWidget(phrase)
        widgetLayOut.addWidget(year)
        widgetLayOut.addWidget(month)
        widgetLayOut.addWidget(day)
        widgetLayOut.addWidget(hour)
        self.format = self.sequence()
        self.formatLabel = QLabel(self.format)
#       xxx = self.getFilename()
#       print(xxx)
        self.file_Label = QLabel("XXX")
        mainLayOut.addWidget(self.formatLabel)
        drop = DragToWidget(self.updateFormat)
        mainLayOut.addWidget(drop)
        buttons = QtGui.QWidget(self)
        closeButton = QtGui.QPushButton("close")
        closeButton.clicked.connect(self.close)
        resetButton = QtGui.QPushButton("reset")
        resetButton.clicked.connect(drop.clear)
        resetButton.clicked.connect(self.reset)
        clearButton = QtGui.QPushButton("clear")
        clearButton.clicked.connect(drop.clear)
        applyButton = QtGui.QPushButton("apply")
        applyButton.clicked.connect(self.setData)
        buttonLayOut = QtGui.QHBoxLayout(buttons)
        buttonLayOut.addWidget(closeButton)
        buttonLayOut.addWidget(applyButton)
        buttonLayOut.addWidget(clearButton)
        buttonLayOut.addWidget(resetButton)
        mainLayOut.addWidget(buttons)
        self.applyButton = applyButton

    def phraseList(self):
        return self._phraseList

    def sequence(self):
        text = ""
        for key in self._phraseList:
            if key in FormatDialog.DICT:
                text = text + FormatDialog.DICT[key]
            else:
                text = text + key
        return text

    def setData(self):
        if self._setData:
            self._setData(self.format)
        pass

    def updateFormat(self, l):
        self._phraseList = l
        self.format = self.sequence()
        self.formatLabel.setText(self.format)

    def reset(self):
        self.updateFormat(self.defaultList)


def config(file):
    if os.path.isfile(file):
        f = open(file)
        l = f.read().split("\n")
        defs = [d for d in l if d.find(":") != -1]
        confDict = dict()
        for d in defs:
            l = d.split(":")
            confDict.update({l[0].strip(): l[1].strip()})
        return confDict


def homeDir():
    home = expanduser("~")
    return home


def currDate(iformat=0):
    format = ["yyyy MMM dd",  "yyyy MM dd"]
    qDate = QtCore.QDate.currentDate()
    return qDate.toString(format[iformat])


class SandboxApp(QtGui.QApplication):

    def __init__(self, *args, **kwargs):
        super(SandboxApp, self).__init__(*args)
        self.mainwindow = QMainWindow()
        self.mainwindow.show()
