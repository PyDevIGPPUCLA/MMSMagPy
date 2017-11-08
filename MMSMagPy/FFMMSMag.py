#ToDos
# 2016 May 03 leel optimize tracing, add hide/show option for traces under grid instance
# 2016 May 03 leel optimize plots, to one data struct, dictor traces under grid instance
# 2016 May 05 leel optimize data processing, cython it
import sys
import os
from os.path import expanduser
from datetime import datetime
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import QSettings
from PyQt4.QtGui import QWidget, QDialog, QCheckBox, QRadioButton
from PyQt4.QtGui import QFileDialog as QtFD
from PyQt4.QtGui import QMainWindow
from PyQt4.QtGui import QApplication, QGraphicsScene
from numpy import amin, amax, zeros, where, empty, arange, array
from MMSMagPy import Ui_MMSMagPy
from FF_File import timeIndex, FF_STATUS, FF_ID, ColumnStats, arrayToColumns
from FF_Time import FFTIME, leapFile
from Parm import isFlatFile
from coordSys import CoordSys
from getTicks import getTicks
from utilities import sliceByTime, BMAG
from sysUtilities import processArgs
from QtUtilities import WARNING, DIALOG, PRINT, printWidget, setStyleSheet, preAmble, MaxGeometry
from mmsPlot import MMSPlot
from process import processing
from plot import Pen
from FFSpectra import FFSpectra
from FFMagUi import FormatDialog, RangeQDial
from bxUtil import MagPlotToolBox, fileStatsDialog, dataDisplay, Hodogram #  , focusPlot
from interval import intervals
from bxProcessQueue import ProcessQueue
from mmsFocus import mmsFocus

#ToDo 2016 jul 21 -> close main  -> close all other windows
# from test import checkFile
__version__ = "1.0.0"


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

MAGCOLS = [[1, 2, 3, 4], [9, 10, 11, 12], [17, 18, 19, 20], [25, 26, 27, 28]]
POSCOLS = [5, 6, 7, 8, 13, 14, 15, 16, 21, 22, 23, 24, 29, 30, 31, 32]
# BLMCOLS = [33, 34, 35, 36, 37, 38, 39, 40, 41]
# BLMCOLS = [32, 33, 34, 35, 36, 37, 38, 39, 40, 41]
BLMCOLS = [32, 33, 34, 35, 36, 37, 38]  #  J{X,Y,Z}M J Jpara, Jperp, Angle


class FFMag(QMainWindow, Ui_MMSMagPy):
    """ main window contains plot"""
    MARGIN = 100
    MAXPOINTS = 2 ** 21  # Maximum records to be read
    MAXPOINTS = 2 ** 19  # Maximum records to be read
    ARGPOINTS = 2 ** 14  # user defined number points to be read
    LAST_PATH = None

    def __init__(self, name="magPy", title="magPy", parent=None, batch=True, file=None,
                 maxGeometry=MaxGeometry, config=None):
        QWidget.__init__(self, parent)
        print("FFMAG batch run FILE : ", file)
        self.epoch = "XXXX"
        self.clear()
        self.config = config   # dict
        self.batch = batch
        self.fname = file
        self.name = name
        self.recentFiles = []
        self._maxGeometry = maxGeometry   # ie display size
        self.numpoints = FFMag.MAXPOINTS  # default number records read
        self.cols = [1, 2, 3, 4]
        self.poss = [5, 6, 7]
        self.count = 0
        self.magData = None
        self.proData = None
        self.BLMData = None
        self.argProcess = False   # need to process args, file is defined
        self.manualSelect = True  # whether file selection is by name or by date
        # data
        self.matrix = [[1, 0, 0], [1, 0, 0], [1, 0, 0]]
        self.eigenValues = [1, 0, 0]
        self.processList = []
        # WIDGETS
        self.ui = Ui_MMSMagPy()
        self.ui.setupUi(self)
        self.nPts = 100
        self.plotSC = [True, True, True, True]
        # actions
        self.setPlots()
        self.setDataControls()
        self.ui.actionBy_Day.triggered.connect(self.daySelect)
        self.ui.actionManually.triggered.connect(self.setFiles)
        self.ui.actionWorking_Directory.triggered.connect(self.dirSelect)
        self.ui.actionFilename.triggered.connect(self.fileFormatSelect)
        self.ui.actionPrint.triggered.connect(self.print_)
        # Quit
#       self.ui.actionQuit.addAction(self.closeEvent)
#       self.ui.actionQuit.addAction(sys.exit)
        self.ui.actionQuit.triggered.connect(self.quit)
#       self.destroyed.connect(self.closeEvent)
#       exitAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
#       exitAction.setShortcut('Ctrl+Q')
#       exitAction.setStatusTip('Exit application')
        self.calDialog = None    # dialog for date
        self.userDialog = None   # dialog for 4 filenames
        self.formatDialog = FormatDialog(self.updateFormatLabel)
        self.workDir = homeDir()    # base directory for merged MMS files, for filename select
        self.baseDir = homeDir()    # base directory for merged MMS files, for calendar select
        # leel 2016 Dec 02, fix this to config file
        self.mmddDir = os.path.join("09", "27")  # subdir by Month and day
        self.workDate = currDate()
        print("WORKDATE", self.workDate)
        self.hour =  None
        self.ffFile = None
        self.FID = None
        if FFMag.LAST_PATH:
            self.workDir = FFMag.LAST_PATH
            self.baseDir = FFMag.LAST_PATH
        else:
            if self.config:
                if 'MMSDATA' in self.config.keys():
                    self.workDir = expanduser(self.config["MMSDATA"])
                    self.baseDir = expanduser(self.config["MMSDATA"])
        if self.config:
            if 'MMSSTART' in self.config.keys():
                self.workDate = self.config["MMSSTART"]
        self.presets()
        self.minWidth = self.width()
        # data
        self.rTime = [0, 0]  # time span records read
        self.pTime = [0, 0]  # time span records plotted
        self.fTime = [0, 0]  # time span of file
        if file is not None:
            self.processArgs()
            self.ffFile = file
            self.hour = file[-2:]
            self.manualSelect = True
            err, mess = self.openFile()  # read in the file
            if err < 1:
                warn = self.openWarn()
                WARNING(self, warn + mess)
                self.FID = None
                exit()
#           self.currFile.setText(file)
#           labels = self.DataSelect["labels"]
#           labels[1].setText(file)
#           if not self.dataToggle.isChecked():
#               self.dataToggle.setChecked(True)
#               self.toggleDataSelection()
#               self.setWindowState(QtCore.Qt.WindowActive)
#           self._FileSet()
            self.refreshMagPlot()
        else:
            self.ui.graphicsView.setStatusTip("Open A File ")
        self.ui.statusbar.showMessage("Welcome to MMSMagPy")
        if batch:  # TEST SECTIONS HERE
            print("PROCESSING IN BATCH MODE")
            width = self.plot_.size.width()
            self.plot_.selection.append(1)
            self.plot_.selection.append(width)
            # qd.applyFilterPanel()
            if (0):
                exit()

    def setPlots(self):
        self.magScene = QGraphicsScene(self.ui.magView)
        self.proScene = QGraphicsScene(self.ui.processedView)
        self.BLMScene = QGraphicsScene(self.ui.BLMView)
        self.magView = self.ui.magView
        self.proView = self.ui.processedView
        self.BLMView = self.ui.BLMView
        self.graphicsView = self.magView   # reference plot for Spectra, Edit modules
        geometry = self.ui.magView.geometry()
        size = geometry.size()
        Pos = QtCore.QPointF(0, size.height())
        Psize = QtCore.QSizeF(geometry.width(), geometry.height())
        self.plotRect = QtCore.QRectF(Pos, Psize)
        tSpanO = FFTIME("2001 001 Jan 01 00:00:00.000", Epoch="Y2000")
        tSpanE = FFTIME("2001 010 Jan 01 23:00:00.000", Epoch="Y2000")
        bounds = QtCore.QRectF(tSpanO.tick, 0, tSpanE.tick, 100)
        self.plot_ = MMSPlot(Pos, Psize, bounds)
        self.plot_.hCent = "Magnetic Field GSE"
        self.plotP = MMSPlot(Pos, Psize, bounds)
        self.plotP.hCent = "PROCESSED DATA"
        self.plotB = MMSPlot(Pos, Psize, bounds)
        self.plotB.hCent = "Magnetic Field BLM"
        self.plot = self.plot_    # reference plot for processQueue
        self.magScene.addItem(self.plot_)
        self.magView.setScene(self.magScene)
        self.proScene.addItem(self.plotP)
        self.proView.setScene(self.proScene)
        self.BLMScene.addItem(self.plotB)
        self.BLMView.setScene(self.BLMScene)

    def collapseDir(self, dir):
        base = dir.replace(expanduser("~"), "~")
        return base

    def openWarn(self):
        base = self.workDir.replace(expanduser("~"), "~")
        warn = "OKAY"
        if not os.path.isdir(self.workDir):
            warn = base + " does not exist"
        else:
            dir = os.path.join(self.workDir, self.mmddDir)
            if not os.path.isdir(dir):
                warn = base + " does not have " + self.mmddDir + " subdirectory"
            else:
                file = os.path.join(self.workDir, self.mmddDir, self.ffFile + ".ffh")
                if not os.path.isfile(file):
                    warn = self.ffFile + " Not found"
        return warn

    def about(self):
        WARNING(self, "DAYSELECT")
        aboutText = "UCLA IGPP 2015"
        reply = QtGui.QMessageBox.question(self, 'Message',
                                           aboutText, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        print(reply)

    def daySelect(self):
        if self.calDialog is None:
            self.calDialog = QDialog(self)
            self.calDialog.setWindowTitle("Set Working Date")
            layOut = QtGui.QGridLayout(self.calDialog)
            self.calendar = QtGui.QCalendarWidget()
            mnDate = QtCore.QDate(2015, 9, 1)
            yyyy, mon, day = currDate(iformat=1).split()
            mxDate = QtCore.QDate(int(yyyy), int(mon), int(day))
            yyyy, mon, day = self.workDate.split()
            stDate = QtCore.QDate(int(yyyy), int(mon), int(day))
            self.calendar.setMinimumDate(mnDate)
            self.calendar.setMaximumDate(mxDate)
            self.calendar.setSelectedDate(stDate)
            applyButton = QtGui.QPushButton("apply", None)
            closeButton = QtGui.QPushButton("close", None)
            applyButton.clicked.connect(self.getWorkDate)
#           applyButton.clicked.connect(self.getWorkDate)
            applyButton.clicked.connect(self.getFilename)
#           applyButton.clicked.connect(self.calDialog.close)
            closeButton.clicked.connect(self.calDialog.close)
            layOut.addWidget(self.calendar, 0, 0, 1, 2)
            layOut.addWidget(closeButton, 2, 0)
            layOut.addWidget(applyButton, 2, 1)
            self.hours = RangeQDial(name=" hour")
#           self.min10 = RangeQDial(maximum=5, name="0 minute")
            if self.hour:
                self.hours.setValue(int(self.hour))
            layOut.addWidget(self.hours, 1, 0, 1, 1)
#           layOut.addWidget(self.min10,1,1,1,1)
        self.calDialog.raise_()
        self.calDialog.show()

    def getWorkDate(self):
        self.workDate = self.calendar.selectedDate().toString("yyyy MMM dd")
#       self.updateWorkDate()

    def getMMDD(self):
        self.workDate = self.calendar.selectedDate().toString("yy MM dd")
        l = list(self.workDate.split(" "))
        fDict = {"year": l[0], "month": l[1], "day": l[2]}
        day = fDict["day"]
        month = fDict["month"]
        return month, day

    def getFilename(self):  # generate filename by date and format
        self.workDate = self.calendar.selectedDate().toString("yy MM dd")
        l = list(self.workDate.split(" "))
        fDict = {"year": l[0], "month": l[1], "day": l[2], "hour": ""}
        pList = self.formatDialog.phraseList()
        fName = ""
        hours = "{0:02d}".format(self.hours.value())
        self.hour = int(hours)
#       min10 = "{0:02d}".format(self.min10.value() * 10)
        for key in pList:
            if key in fDict:
                word = fDict[key]
                fName = fName + word
            else:
                fName = fName + key
        if self.manualSelect:
#           self.dataToggle.setChecked(False)
#           self.toggleDataSelection()
#           self.setWindowState(QtCore.Qt.WindowActive)
            month, day = self.getMMDD()
            self.mmddDir = os.path.join(month, day)
#       self.currFile.setText(fName)
#       self.ffFile = fName + hours + min10
        self.ffFile = fName + hours
        #  check if there's a year subdir and change workdir
        year = "20" + fDict["year"]
#       day = fDict["day"]
#       month = fDict["month"]
#       print(self.mmddDir)
        nPath = os.path.join(self.workDir, year)
        if os.path.isdir(nPath):
            self.workDir = nPath
            text = self.DataSelect["dir"]
            text.setText(nPath.replace(expanduser("~"), "~"))
        if self.FID:
            self.FID.close()
            self.FID = None
        openFile = self._setFile()
        if openFile:
            self.calDialog.close()
        return fName

    def userSelect(self):
        if self.userDialog is None:
            self.userDialog = QDialog(self)
            self.userDialog.setWindowTitle("Set file")
            self.calendar = QtGui.QCalendarWidget()
            mnDate = QtCore.QDateTime.fromString("2015 Sep 27", "yyyy mmm dd")
            stDate = QtCore.QDateTime.fromString(self.workDate, "yyyy mmm dd")
            self.calendar.setMinimumDate(mnDate)
            self.calendar.setSelected(stDate)
            applyButton = QtGui.QPushButton("apply", None)
            closeButton = QtGui.QPushButton("close", None)
            applyButton.clicked.connect(self.getFiles)
            closeButton.clicked.connect(self.userDialog.close)
#           applyButton.clicked.connect(self.getFiles)
#           closeButton.clicked.connect(self.userDialog.close)
        self.userDialog.raise_()
        self.userDialog.show()

    def userSelect4(self):
        if self.userDialog is None:
            self.userDialog = QDialog(self)
            self.userDialog.setWindowTitle("Set files")
            layOut = QtGui.QGridLayout(self.userDialog)
            text0 = QtGui.QLabel("FILE 1")
            text1 = QtGui.QLabel("FILE 2")
            text2 = QtGui.QLabel("FILE 3")
            text3 = QtGui.QLabel("FILE 4")
            butt0 = QtGui.QPushButton("Set")
            butt1 = QtGui.QPushButton("Set")
            butt2 = QtGui.QPushButton("Set")
            butt3 = QtGui.QPushButton("Set")
            self.calendar = QtGui.QCalendarWidget()
            applyButton = QtGui.QPushButton("apply", None)
            closeButton = QtGui.QPushButton("close", None)
            butt0.clicked.connect(self.setFiles)
            butt1.clicked.connect(self.setFiles)
            butt2.clicked.connect(self.setFiles)
            butt3.clicked.connect(self.setFiles)
            applyButton.clicked.connect(self.getFiles)
            closeButton.clicked.connect(self.userDialog.close)
            layOut.addWidget(text0, 0, 1, 1, 1)
            layOut.addWidget(text1, 1, 1, 1, 1)
            layOut.addWidget(text2, 2, 1, 1, 1)
            layOut.addWidget(text3, 3, 1, 1, 1)
            layOut.addWidget(butt0, 0, 0, 1, 1)
            layOut.addWidget(butt1, 1, 0, 1, 1)
            layOut.addWidget(butt2, 2, 0, 1, 1)
            layOut.addWidget(butt3, 3, 0, 1, 1)
            layOut.addWidget(applyButton, 5, 0)
            layOut.addWidget(closeButton, 5, 1)
            self.files = {butt0: text0, butt1: text1, butt2: text2, butt3: text3}
        self.userDialog.raise_()
        self.userDialog.show()

    def setFiles(self, PATH=None):
        """ flatfile selection dialog , manual selection"""
        options = QtFD.ReadOnly  # |QtFD.DontUseNativeDialog
        if PATH:
            path = PATH
        else:
            path = self.workDir
        QQ = QtFD(self)
        QFILTER = QtGui.QSortFilterProxyModel(self)
        QFILTER.invalidateFilter()
        rx = QtCore.QRegExp("*.ffd")
        rx.setPatternSyntax(QtCore.QRegExp.Wildcard)
        QFILTER.setFilterRegExp(rx)
        model = QtGui.QFileSystemModel()
        model.setNameFilters(["*.ffd"])
        model.setNameFilterDisables(False)
        QFILTER.setSourceModel(model)
        QQ.setProxyModel(QFILTER)
        QQ.setFilters(["*.ffd]"])
        QQ.setNameFilter("*.ffd")
        QQ.setDirectory(path)
        fullname = QQ.getOpenFileName(self, caption="FlatFile", options=options)
        if fullname is "":
            return (0, "NO FILE")
        self.fname = fullname.rsplit(".", 1)[0]
        if self.fname is None:
            return (0, "NO FILE")
        if hasattr(self, "files"):
            text = self.files[self.sender()]
            text.setText(fullname)
        if not self.manualSelect:
#           self.dataToggle.setChecked(True)
            self.toggleDataSelection()
            self.setWindowState(QtCore.Qt.WindowActive)
#       labels = self.DataSelect["labels"]
#       fName = os.path.basename(fullname)
#       bName = os.path.splitext(fName)
#       home = expanduser("~")
#       dPath = fullname.replace(home, "~")
#       bPath = os.path.dirname(dPath)
#       labels[0].setText(bPath)
#       labels[1].setText(bName[0])
#       self.workDir = bPath
#       self.ffFile = bName[0]
#       self.mmddDir = ""
        openFile = "self._setFile()"
        return openFile

    def getFiles(self):
        # NOT Filtering only FF files
        self.fileSet = [item.text() for k, item in self.files.items()]
        self.updatePlotControlGroupBox()

    def dirSelect(self, PATH=None):
        """ working directory selection dialog """
        path = self.workDir
        if PATH:
            path = PATH
        QQ = QtFD(self, "MMS HOME", path)
        fullname = QQ.getExistingDirectory(self)  # directory=expanduser(path), caption="MMS BASE")
        if fullname is "":
            return (0, "NO DIRECTORY")
#       home = expanduser("~")
#       dPath = fullname.replace(home, "~")
#       text = self.DataSelect["dir"]
#       text.setText(dPath)
        self.workDir = fullname

    def fileFormatSelect(self):  # m1a150319
        if self.formatDialog is None:
            self.formatDialog = FormatDialog(self.updateFormatLabel)
        self.formatDialog.show()

    def set(self):
        pass

    def quit(self):
        panelTypes = {self.hodogram, self.focus, self.spectra, self.queueDisplay}
        for panels in panelTypes:
            for p in panels:
                if p:
                    p.close()
#       reply = QtGui.QMessageBox.question(self, 'Message',
#                                          "Are you sure to quit?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
#       if reply == QtGui.QMessageBox.Yes:
        exit()

    def genStatTable(self):
        rows = 4
        cols = 8
        HLabels = ["mms1 Min", "mms1 Max", "mms2 Min", "mms2 Max",
                   "mms3 Min", "mms3 Max", "mms4 Min", "mms4 Max"]
        VLabels = ["Bx", "By", "Bz", "Bt"]
        fileStat = QtGui.QTableWidget(rows, cols, self)
        fileStat.setAutoFillBackground(True)
        fileStat.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        fileStat.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        fileStat.setHorizontalHeaderLabels(HLabels)
        fileStat.setVerticalHeaderLabels(VLabels)
        fileStat.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        fileStat.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        width = fileStat.columnWidth(1) * 8 + fileStat.verticalHeader().width() * 2
        height = fileStat.rowHeight(1) * 4 + fileStat.horizontalHeader().height()
        fileStat.setMinimumWidth(width)
        fileStat.setMinimumHeight(height)
        fileStat.setMaximumHeight(height)
        self.fileStat = fileStat
#       cells = [0] * 4
#       cells[0] =  [1, 2]
#       cells[1] =  [2, 2]
#       cells[2] =  [3, 2]
#       cells[3] =  [4, 2]
#       print(cells)
#       for r in range(rows):
#           for c in range(cols):
#               item = QtGui.QTableWidgetItem('%s' % "{:9.6f}".format(cells[r][c]))
#               fileStat.setItem(r, c, item)
        return

    def fillFileStat(self):
        if self.stats is None:
            return
        if self.fileStat is None:
            return
        rows = 4
        cols = 2
        cells = self.stats
        for r in range(rows):
            for c in range(cols):
                item = QtGui.QTableWidgetItem('%s' % "{:9.6f}".format(cells[r][c + 1]))
                self.fileStat.setItem(r, c, item)

    def fillFileStat16(self):
        if self.stats is None:
            return
        if self.fileStat is None:
            return
        rows = 4
        cols = 16
        cells = self.stats16
        for r in range(rows):
            for c in range(cols):
                item = QtGui.QTableWidgetItem('%s' % "{:9.6f}".format(cells[r][c + 1]))
                self.fileStat.setItem(r, c, item)

    def hello(self):
        print("Hello")

    def setDataControls(self):
        self.hodogramInterval = intervals(label=["Hodogram"])
        self.spectraInterval = intervals(label=["Spectral"])
        self.focusInterval = intervals(label=["Focus"])
        self.hodogram = [None] * 4
        self.spectra = [None] * 4
        self.focus = [None] * 4
        self.ui.statButton.clicked.connect(self.showStats)
        self.ui.headerButton.clicked.connect(self.showHeader)
        self.ui.dataButton.clicked.connect(self.showData)
        self.ui.hodoButton.clicked.connect(self.showHodogram)
        self.ui.focusButton.clicked.connect(self.showFocus)

    def showStats(self):
        if self.statDisplay is None:
            self.genStatTable()
            self.fillFileStat16()
            self.fileStat.resizeColumnsToContents()
            QD = QDialog(self)
            QD.setWindowTitle(self.ffFile)
            QD.setGeometry(0, 0, 1000, 300)
            layOut = QtGui.QFormLayout(QD)
            layOut.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
            layOut.addWidget(self.fileStat)
            self.statDisplay = QD
        self.statDisplay.show()
        self.statDisplay.raise_()
        self.statDisplay.adjustSize()

    def showHeader(self):
        if self.dataDisplay is None:
            self.fileDisplay = fileStatsDialog(Title=self.ffFile, FID=self.FID)
        self.fileDisplay.show()

    def showData(self):
        if self.FID is not None:
            self.dataDisplay = dataDisplay(self.FID, self.times, self.magData, Title=self.ffFile)
        self.dataDisplay.show()

    def genPlotControls(self):
        plotGB = self.ui.plotGB
        plotLO = QtGui.QGridLayout(plotGB)
        self.toolBox = MagPlotToolBox()
#       self.toolBox = MagPlotTab()
        self.toolBox.addActions(self.setpTime)
        self.toolBox.addActions(self.resetMagPlot)
#       self.toolBox.removeItem(2)
        plotLO.addWidget(self.toolBox)
        traceW = QWidget(self)  # contains toggles to display sc traces
        traceLO = QtGui.QGridLayout(traceW)
        plotLO.addWidget(traceW)
        self.SCCB = [0] * 4
        scPens = self.plot_.pens()
        for i in range(4):
            label = "MMS" + str(i + 1)
            SCCB = QCheckBox(label, self)
            SCCB.setChecked(self.plotSC[i])
#           SCCB.setAutoFillBackground(True)
            p = SCCB.palette()
            pen = scPens[i]
            p.setColor(SCCB.foregroundRole(), pen.color())
            SCCB.setPalette(p)
            SCCB.clicked.connect(self.toggles)
            self.SCCB[i] = SCCB
            traceLO.addWidget(self.SCCB[i], 0, 2 * i + 1)
#       DataCB = QCheckBox("processed", self)
#       DataCB.clicked.connect(self.togglePlot)
#       DataCB.setEnabled(False)
#       traceLO.addWidget(DataCB, 0, 9)
#       self.DataCB = DataCB
        dataGB = self.ui.dataGB
        dataLO = QtGui.QGridLayout(dataGB)
        dataLO.addWidget(self.ui.editButton, 0, 1)
        dataLO.addWidget(self.ui.spectraButton, 0, 2)
        self.SCRB = [0] * 4
        # radio select which data from which spacecraft
        for i in range(4):
            label = "MMS" + str(i + 1)
            SCRB = QRadioButton(label, self)
            SCRB.clicked.connect(self.selectSC)
            dataLO.addWidget(SCRB, 0, i + 3)
            self.SCRB[i] = SCRB
        self.SCRB[0].setChecked(True)
#       self.stat
#       self.DataSelect = {"labels": labels, "date": dateTime, "dir": dirLabel,
#                          "format": forLabel}   # save Widgets here
#       self.updateWorkDate()
#       self.ui.plotGB.repaint()
        pass

    def toggles(self):
        for i in range(4):
            self.plotSC[i] = self.SCCB[i].isChecked()
        self.redrawMagPlot()
        if self.focus[0]:
            spaceCraft = where(self.plotSC)[0]
            self.focus[0].setSpaceCraft(spaceCraft)
        print("MAKE self.focus[0].refresh()")

    def togglePlot(self):
        if self.DataCB.isChecked():
            self.plot_.show()
#           self.plotC = self.plot_
            self.plotP.hide()
        else:
            if self.dataP:
                self.plot_.hide()
#               self.plotC = self.plotP
                self.plotP.hide()

    def selectSC(self):
        for i in range(4):
            if self.SCRB[i].isChecked():
                self.currSc = i
                self.cols = [i * 8 + j + 1 for j in range(4)]

    def whichSC(self):
        for i in range(4):
            if self.SCRB[i].isChecked():
                return i
        return 0

    def setEditActions(self):
        self.ui.spectraButton.setEnabled(False)
        self.ui.spectraButton.clicked.connect(self.showSpectra)
        self.spectraInterval = intervals(label=["Spectra init"])
        self.ui.editButton.setEnabled(False)
        self.ui.editButton.clicked.connect(self.processQueue)


# Todo llee 2016 Jul 22 make super module,???
#   drawIntervalPanel(self, {focus, hodo, spectral}
#   showIntervalPanel(self, {focus, hodo, spectral}

# leel 2016 Dec 01 one focus panel for four spacecraft vs one each
    def drawFocus(self):
        """ used in mmsPlot Event Handler """
        spaceCraft = where(self.plotSC)[0]
#       mms = self.whichSC()
        mms = 0
        if self.focus[mms]:
            self.focus[mms].close()
        self.timeO = FFTIME(self.times[0], Epoch=self.epoch)
        self.timeE = FFTIME(self.times[-1], Epoch=self.epoch)
        self.focus[mms] = mmsFocus(data=self)
        self.focus[mms].spaceCraft = spaceCraft
        self.focus[mms].setPens(MMSPlot.Pens)
        self.focus[mms].show()
        self.focus[mms].raise_()

    def showFocus(self):
        self.selectPrompt("Focus")
        self.focusInterval.setPen(Pen.Green)
        self.focusInterval.setLabel("Focus")
        self.focusSlot = self.drawFocus
        self.plot_.setClientInterval(self, self.focusInterval)
        self.plot_.resetSelections()

    def drawHodogram(self):
        """ used in mmsPlot Event Handler """
        mms = self.whichSC()
        if self.hodogram[mms]:
            self.hodogram[mms].close()
        self.timeO = FFTIME(self.times[0], Epoch=self.epoch)
        self.timeE = FFTIME(self.times[-1], Epoch=self.epoch)
        self.hodogram[mms] = Hodogram(data=self)
        self.hodogram[mms].setEigenValues(self.eigenValues)
        self.hodogram[mms].setMatrix(self.matrix)
        self.hodogram[mms].show()
        self.hodogram[mms].raise_()

    def showHodogram(self):
        self.selectPrompt("Hodogram")
        self.hodogramInterval.setPen(Pen.Green)
        self.hodogramInterval.setLabel("Hodogram")
        self.focusSlot = self.drawHodogram
        self.plot_.setClientInterval(self, self.hodogramInterval)
        self.plot_.resetSelections()

    def drawSpectra(self):
        """ used in mmsPlot Event Handler """
        mms = self.whichSC()
        if self.spectra[mms]:
            self.spectra[mms].close()
        self.timeO = FFTIME(self.times[0], Epoch=self.epoch)
        self.timeE = FFTIME(self.times[-1], Epoch=self.epoch)
        self.spectra[mms] = FFSpectra(name="Spectra Analysis", title=self.fname, parent=None, data=self)
        self.spectra[mms].show()
        self.spectra[mms].raise_()

    def showSpectra(self):
        self.selectPrompt("Spectra")
        self.spectraInterval.setPen(Pen.Blue)
        self.spectraInterval.setLabel("Spectra")
        self.focusSlot = self.drawSpectra
        self.plot_.setClientInterval(self, self.spectraInterval)
        self.plot_.resetSelections()
        self.spectraInterval.clear()

    def printSelf(self):
        printWidget(self)

    def updateFormatLabel(self, text):
#       label = self.DataSelect["format"]
#       label.setText(text)
        pass

    def _setFile(self):  # check if selection is viable, open file and plot
#       self.currFile.setText(self.ffFile)
#       if self.dataToggle.isChecked():
#           print("_SET FILE work", self.workDir, "MMDD", self.mmddDir, "FName", self.ffFile)
#           path = expanduser(os.path.join(self.workDir))
#       else:
#           path = expanduser(os.path.join(self.baseDir, self.mmddDir))
#           print("_SET FILE base", self.baseDir, "MMDD", self.mmddDir, "FName", self.ffFile)
        path = expanduser(os.path.join(self.workDir, self.mmddDir))
        absFile = os.path.join(path, self.ffFile)
        isFlat = isFlatFile(absFile, None)
        if not isFlat:
            print(self.workDir, self.ffFile)
            mess = "_setFile" + self.collapseDir(absFile) + " not found."
            DIALOG(self, mess)
            return False
        self.openFile()
        return True

    def _NewFile(self, PATH=None):  # slot when Open Button clicked
        err, msg = self.openFile(PATH=PATH)
        if err < 0:
            print(msg, PATH)
            WARNING(self, "Unable to open " + self.fname)
            return None
        if err == 0:
            DIALOG(self, "No File Selected")
            return 0

    def setpTime(self):
        start, stop_ = self.toolBox.timeBounds()
        tO = FFTIME(start, Epoch=self.epoch)
        tE = FFTIME(stop_, Epoch=self.epoch)
        self.pTime = [tO.UTC, tE.UTC]
#       self.toolBox.setTimeBounds(Plot=self.pTIme)
        # redo plot

    def print_(self):  # print MagPlot graph
        self.printer = PRINT(self.magView)

    def printPanel(self):  # print Containing MagPlot widget
        self.printer = printWidget(self)

    def closeEvent(self, event):  # clean up
        reply = QtGui.QMessageBox.question(self,
                                           "Message", "Quit MMSMag?",
                                           QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
            return
        if self.FID is not None:
            self.FID.close()
        panelTypes = [self.hodogram, self.focus, self.spectra, self.queueDisplay]
        for panels in panelTypes:
            for p in panels:
                if p:
                    p.close()
        exit()

    def clear(self):
        """ clear program configuration """
        if hasattr(self, 'FID'):
            if self.FID is not None:
                self.FID.close()
        self.batch = False
        self.fname = None
        self.name = None
        self.FID = None
        self.recentFiles = []

    def openFile(self, PATH=None):  # slot when Open pull down is selected
        """ flatfile selection dialog """
        if self.manualSelect:
            print("OPEN FILE work", self.workDir, "MMDD", self.mmddDir, "FName", self.ffFile)
            fFile = expanduser(os.path.join(self.workDir, self.mmddDir, self.ffFile))
        else:
            fFile = expanduser(os.path.join(self.baseDir, self.mmddDir, self.ffFile))
            print("OPEN FILE base", self.baseDir, "MMDD", self.mmddDir, "FName", self.ffFile)
        FID = FF_ID(fFile, status=FF_STATUS.READ | FF_STATUS.EXIST)
        if not FID:
            WARNING(self, "NOT HAPPENING")
            return -1, "BAD"
        if self.FID is not None:
            self.FID.close()
            self._NoData()   # purge old panels
        self.FID = FID
        self.epoch = self.FID.getEpoch()
        info = self.FID.FFInfo
        err = self.FID.open()
        if err < 0:
            return err, " UNABLE TO OPEN"
        err, mess = self.loadFile()  # read in the file
        if err < 0:
            return err, mess
        self.fTime = [info["FIRST_TIME"].info, info["LAST_TIME"].info]
        self.resolution = self.FID.getResolution()
#       self.numpoints = min(self.numpoints, self.FID.FFParm["NROWS"].value)
        self.plot_.clear()
#       self.setHeaders(self.plot_)
        self.calibrateMMSPlot(self.plot_, "self.graphs")  # set axis bounds from data
        self.calibrateMMSPlot(self.plotP, "self.graphs")  # set axis bounds from data
        self.calibrateMMSPlot(self.plotB, "self.graphs")  # set axis bounds from data
        self.setTraces()
        self.updateToolBox()
        self.magScene.update(self.plotRect)  # refresh plot
        self._HasData()
        self.magView.show()
#       self.initSliders()
#       self._HasData()  # enable file dependent widgets
#       print("    END OPEN FILE")
        return 1, "FILE " + self.fname + "read"

    def updateFileStats(self):
        self.ui.fileStatsGB.setTitle("File : " + self.ffFile)
        self.ui.dirLabel.setText(self.workDir)
#       tO = FFTIME(self.times[0], Epoch=self.epoch)
#       tE = FFTIME(self.times[-1], Epoch=self.epoch)
#       self.ui.startTimeLabel.setText(tO.UTC)
#       self.ui.stop_TimeLabel.setText(tE.UTC)

    def updateToolBox(self):
        tb = self.toolBox
        tO = FFTIME(self.times[0], Epoch=self.epoch)
        tE = FFTIME(self.times[-1], Epoch=self.epoch)
        tBounds = [tO.UTC, tE.UTC]
#       tb.setTimeBounds(Current=tBounds, Data=self.rTime, Plot=self.pTime)
        tb.setTimeBounds(Current=tBounds, Data=self.rTime, Plot=self.pTime, FileSpan=self.fTime)
        plotParms = self.autoScaling
        tb.setYBounds(Scale=plotParms[0], Above=plotParms[1], Below=plotParms[2])
        tb.setColumnSelection(Columns=self.cols, FID=self.FID)

    def loadFile(self):
        if self.FID is None:
            print("PROBLEM", self.ffFile)
            quit()
        nRows = self.FID.getRows()
        records = self.FID.DID.sliceArray(row=1, nRow=nRows)
        self.times = records["time"]
        self.dataByRec = records["data"]
        self.dataByCol = arrayToColumns(records["data"])
        self.data = self.dataByCol    # for FFSpectrar
        self.epoch = self.FID.getEpoch()
        UTCO = FFTIME(self.times[0], Epoch=self.epoch)
        UTCE = FFTIME(self.times[-1], Epoch=self.epoch)
        self.rTime = [UTCO.UTC, UTCE.UTC]
        self.pTime = [UTCO.UTC, UTCE.UTC]
        magData = []
#       print(self.dataByRec.shape)
        for i in range(4):
            for j in range(4):
                column = self.dataByRec[:, i * 8 + j]
                magData.append(column)
        BLMData = []
#       print("BLMCOLS", BLMCOLS)
#       print(self.dataByRec.shape)
        for i in BLMCOLS:
            column = self.dataByRec[:, i]
            BLMData.append(column)
        magStats = ColumnStats(magData, self.FID.getError(), NoTime=True)
        BLMStats = ColumnStats(BLMData, self.FID.getError(), NoTime=True)
        self.stats16 = magStats
        self.magData = magData
        self.BLMData = BLMData
        self.stats = self.condenseStats(magStats)   # merge the four spacecraft to one
        self.BLMStats = BLMStats
#       self.fillFileStat()
        self.updateFileStats()
        return 1, "OKAY"

    def condenseStats(self, stats, NVectors=4):  # redo stats 4 (bx,by,bz,bt)
        functions = (amin, amin, amax, amin, amax, amin)
        nStats = len(stats)
        l = [0] * NVectors
        for i in range(NVectors):
            l[i] = []
            for j in range(NVectors):
                index = j * 4 + i + 1
                l[i].append(index)
        newStats = zeros([nStats, 5])
        for i in range(nStats):
            stat = stats[i]
            newStats[i, 0] = 0
            for j in range(NVectors):
                valuesList = [stat[v] for v in l[j]]
                newValue = functions[i](valuesList)
                newStats[i, j + 1] = newValue
        return newStats

    def processQueue(self):
        mms = self.whichSC()
        if self.queueDisplay[mms]:
            self.queueDisplay[mms].close()
            self.queueDisplay[mms] = None
        plotParms = getTicks(self.stats, self.cols)
        tO = FFTIME(self.times[0], Epoch=self.epoch)
        tE = FFTIME(self.times[-1], Epoch=self.epoch)
        times = (tO, tE, self.epoch)
        self.queueDisplay[mms] = ProcessQueue(dataArray=self.BMag,  # action getting data
                                              PlotParms=plotParms,  # action refresh GraphicsItem
                                              Times=times,
                                              Title=self.fname,
                                              reference=self)  # ProcessQueue Link
        self.queueDisplay[mms].setWindowName("Process Queue mms" + str(mms + 1))
        self.queueDisplay[mms].show()
        self.queueDisplay[mms].raise_()

    def extractData(self, numberRecords, PAD=False, Filter=True):
        # wrapper for extractData
        data = self.extractDataFromBuffer(numberRecords, PAD=PAD, Filter=Filter)
        self.dataExtract = data

# ToDoes leel 2016 Jul 22 make this external

    def extractDataFromBuffer(self, numberRecords, PAD=False, Filter=True):
        # generate BMAG instance where prepend/append numberRecords to the current
        #    plot span
        # function used in Filter class
        # self.tO, self.tE -> plot start/stop times
        # self.rO, self.rE -> data read start/stop times
        # self.fO, self.fE -> file start/stop times
        # method
        # self.times, self.data -> data already read (buffered)
        #   determine start/stop indices in buffer
        # if the indices are beyond what is alredy read,
        #    read the missing section
        #  if indices are beyond the file contents, fill with first/last data point
        # did  not account for reading and padding
        #   did test for reading part/ partial read
        FFID = self.FID
        # determine number records used in plot
        times = self.times
        iO = timeIndex(times, self.tO)
        iE = timeIndex(times, self.tE)
        nTimes = times.size
        # create buffer
        span = iE - iO + 1
        nItems = span + numberRecords * 2
        # numpy.set_printoptions(formatter={'float': '{:8.0f}'.format})
        T = zeros(nItems + 1)
        X = zeros(nItems + 1)
        Y = empty(nItems + 1)
        Z = empty(nItems + 1)
        B = empty(nItems + 1)
        # Fill data from buffer (self.times, self.data)
        jO = iO - numberRecords
        jE = iE + numberRecords
        lO = jO if jO > 0 else 0
        lE = jE if jE < nTimes else nTimes
        LO = 0 if jO >= 0 else -jO
        LE = LO + lE - lO
        # print("iO",iO,"iE",iE)
        # print("jO",jO,"jE",jE)
        # print("lO",lO,"lE",lE)
        # print("LO",LO,"LE",LE, "LO+JE", LO + jE, "LO+nTIMES",LO + nTimes)
        x, y, z, b = self.cols
        T[LO:LE] = times[lO:lE]
        X[LO:LE] = self.data[x - 1][lO:lE]
        Y[LO:LE] = self.data[y - 1][lO:lE]
        Z[LO:LE] = self.data[z - 1][lO:lE]
        B[LO:LE] = self.data[b - 1][lO:lE]
        #printHeadTail(T[LO-3:LE+3],6, "FROM BUFFER T LO:LE")
        #printHeadTail(X[LO-3:LE+3],6, "FROM BUFFER X")
        # fill where data is beyond the current buffer
        dt = FFID.getResolution()
        if jO < 0:   # more data needed before current buffer
            #print("NEED TO PAD AHEAD")
            # check if there's unread data if need be pad rest
            paddingRequired = True
            if times[0] > self.fO:  # file and more data
                #print("FILL FROM FILE NOT TESTED")
                paddingRequired = False
                t = times[0] - LO * dt
                if t > self.fO:  # only partial
                    first = FFID.ffsearch(t, 1, LO)
                    lo = 0
                    nRow = LO
                    paddingRequired = True
                else:
                    first = 1
                    lo = (self.fO - t) / dt
                    nRow = int(LO - lo + 1)
                    paddingRequired = False
                fData = self.FID.DID.sliceArray(row=first, nRow=nRow)
                data = arrayToColumns(fData["data"])
                T[lo:LO] = fData["time"]
                X[lo:LO] = data[x - 1]
                Y[lo:LO] = data[y - 1]
                Z[lo:LO] = data[z - 1]
                B[lo:LO] = data[b - 1]
                if paddingRequired:
                    LO = lo
                # printHeadTail(T[0:LO+3],6, "FROM FILLER T 0:LO")
                # check if last line is < number record
                # if so more padding is require and set pad number
            if paddingRequired:
#               print("FILL BY PADDING O LO ",LO)
                t = times[0] - LO * dt
                T[0:LO] = t + arange(0, LO) * dt
                X[0:LO].fill(X[LO])
                Y[0:LO].fill(Y[LO])
                Z[0:LO].fill(Z[LO])
                B[0:LO].fill(B[LO])
        #printHeadTail(T[0:LO+3],6, "TIME 0 LO")
        #printHeadTail(X[0:LO+3],6, "X O LO")
        if jE > nTimes:  # more Data required after buffer
#           print("FILL END ", jE)
            # check if there's unread data if need be pad rest
            paddingRequired = True
            totalRecords = FFID.DID.nrows
            dn = 0
            t = times[-1] + dt / 2
            if t < self.fE:  # need to read from file
#               print("FILL BY READING NOT TESTED", nTimes, LE, times[-1])
                paddingRequired = False
                first = FFID.ffsearch(times[-1], nTimes, LE)
                t = times[-1] + T[LE:].size * dt
                if t > self.fE:  # only partial
                    paddingRequired = True
                    nRow = FFID.DID.nrows - (t - self.fE) / dt
                else:
                    paddingRequired = False
                    nRow = jE - nTimes + 2
                first = FFID.ffsearch(t, nTimes, totalRecords)
                if not first:
                    # no data
                    print("FFMagPlot.py: THERES A PROBLEM GETTING SLICE")
                    print("TIME", t, FFTIME(t, Epoch=self.epoch).UTC)
                    print("FILE", self.fE, FFTIME(self.fE, Epoch=self.epoch).UTC)
                    paddingRequired = True
                    exit(1)
                print(first, nRow)
                fData = self.FID.DID.sliceArray(row=first, nRow=first + nRow - 1)
                # 2015 Jun 29
                #fData = self.FID.DID.sliceArray(row=first, nRow=nRow-1)
                if fData is None:
                    print("oh snap")
                    print(first, first + nRow)
                    exit(1)
                data = arrayToColumns(fData["data"])
                T[LE:] = fData["time"]
                X[LE:] = data[x - 1]
                Y[LE:] = data[y - 1]
                Z[LE:] = data[z - 1]
                B[LE:] = data[b - 1]
                dn = fData["time"].size
                if fData["time"][-1] < t:
                    paddingRequired = True
                    LE = LE + fData["time"].size
                # check if last line is < number record
                # if so more padding is require and set pad number
            if paddingRequired:
#               print("FILL BY PADDING")
                t = times[-1] + dt
                # print(jE, nTimes, fData["time"].size)
                n = jE - nTimes + 2 - dn
                T[LE:] = t + arange(0, n) * dt
                X[LE:].fill(X[LE - 1])
                Y[LE:].fill(Y[LE - 1])
                Z[LE:].fill(Z[LE - 1])
                B[LE:].fill(B[LE - 1])
#       printHeadTail(T[LO-3:LE+3],6, "FROM BUFFER T LO:LE")
#       printHeadTail(X[LE-3:LE],6, "FROM BUFFER X")
        flag = FFID.FFInfo["ERROR_FLAG"].value
        b = BMAG(T, X, Y, Z, B, Flag=flag, Limit=4)
        b.plotBounds = [self.tO, self.tE]
        b.errorFlag = flag
        b.epoch = FFID.FFParm["EPOCH"].value
        return b

    def processData(self):
        # when new data is loaded generate the corresponding processed data
        # generates data for all 4 spacecraft
        print("    PROCESS THE DATA")
#       ticks = [t.tick for t in times]
        Bseries = [0] * 16
        d = self.data
        for i in range(4):            # bx, by, bz, bt
            cols = MAGCOLS[i]
            iO = i * 4
            iE = iO + 4
            processedData = processing(self.processList, self.times,
                                        d[cols[0]], d[cols[1]], d[cols[2]], d[cols[3]])
            Bseries[iO: iE] = processedData[1:]
            if i is 0:
                self.timeP = processedData[0]
        self.proData = Bseries

    def processUpdated(self):
        print("    Update process")
        # when a new process sequence is applied update parameters and data
        #       self.processQueue = self.queueDisplay.processorList()
        mms = self.whichSC()
        self.processList = self.queueDisplay[mms].processorList()
        self.generators = self.queueDisplay[mms].generatorList()
        if self.processQueue:
            self.processData()   # apply to all four spacecraft
        self.ui.plotTabs.setCurrentIndex(1)
        self.redrawMagPlot()

#   def BLMUpdated(self):   # dummy for now
#       self.BLMData = self.magData / 2

    def setMagPlot(self, plot, graphs):
        """ new data read in -> re-plots plot """
        plot.clear()
        self.setHeaders(plot)
        self.calibrateMagPlot(plot, graphs)  # set axis bounds from data
        self.refreshMagPlot()

    def resetMagPlot(self):
        """ SLOT FOR APPLY and CLOSE
        toolBox action for apply
        grab scale, above, below, to,te and columns
        """
        print("RESET MAGPLOT")
        toolBox = self.toolBox
        start, stop_ = toolBox.timeBounds()
        cols = toolBox.columnSelection()
        self.tO = FFTIME(start, Epoch=self.epoch).tick
        self.tE = FFTIME(stop_, Epoch=self.epoch).tick
        self.cols = cols
        if toolBox.AutoScale.isChecked():
            plotParms = self.autoScaling
        else:
            scale, above, below = toolBox.YBounds()
            plotParms = (scale, above, below)
        self.plot_.resetBounds(plotParms, (self.tO, self.tE,
                                          self.epoch))
        self.plotP.resetBounds(plotParms, (self.tO, self.tE,
                                           self.epoch))
        self.redrawMagPlot()
#       self.plot_.clear()
        # processed Data  Plot
#       self.setTraces()
#       self.magScene.update(self.plotRect)  # refresh plot
#       self.magView.show()
#       self.magView.scene().update()

    def redrawMagPlot(self):
        """ clear out current traces, and redraw traces"""
        plots = [self.plot_, self.plotP, self.plotB]
        index = self.ui.plotTabs.currentIndex()
        plots[index].clear()
        self.refreshMagPlot()
        self.setTraces()

    def refreshMagPlot(self):
        """ refreshes plot """
        tags = ["mag", "pro", "BLM"]
        plots = {
            "mag": {"scene": self.magScene, "plot": self.plot_, "view": self.magView},
            "pro": {"scene": self.proScene, "plot": self.plotP, "view": self.proView},
            "BLM": {"scene": self.BLMScene, "plot": self.plot_, "view": self.BLMView},
            }
        index =  self.ui.plotTabs.currentIndex()
        panel = plots[tags[index]]
        panel["plot"].hRigh = datetime.now().strftime('%Y %j %b %d %H:%M:%S')
        panel["plot"].hLeft = self.ffFile
        panel["scene"].update(self.plotRect)  # refresh plot
        panel["scene"].update()
        panel["view"].show()

    def setHeaders(self, plot):
        """
        set MagPlot annotations
        """
        # HeaderLeft -> filename , HeaderRight -> source
        # FooterLeft -> SC Coords, FooterRight -> timeStamp
        if 1:   # debug leel
            return
        plot.hLeft = self.fname.rsplit("/", 1)[-1]
        tail = self.fname.rsplit("/", 1)
        if tail is not None:
            plot.hLeft = tail[-1]
        else:
            plot.hLeft = self.fname
        desc = self.FID.getColumnDescriptor("SOURCE")
        name = self.FID.getColumnDescriptor("NAME")
        plot.hRigh = desc[0]
        system = CoordSys(name[2], desc[2])
        if system is not None:
            plot.fLeft = system + " COORDINATES"
        plot.fRigh = datetime.now().strftime('%Y %j %b %d %H:%M:%S')

    def calibrateMMSPlot(self, plot, graphs):
        """ calibrate plot bounds from data"""
        # plotParms -> scale, above, below
#       nCols = self.FID.getNColumns()
#       cols =  [i for i in range(2, nCols)]
        cols = [1, 2, 3, 4]
        plotParms = getTicks(self.stats, cols)
        BLMParms = getTicks(self.BLMStats, cols)
        self.autoScaling = plotParms
        self.tO = self.times[0]
        last = min(self.numpoints - 1, len(self.times) - 1)
        self.tE = self.times[last]
        plot.resetBounds(plotParms, BLMParms, (self.tO, self.tE, self.FID.getEpoch()))
#       self.setTraces()

    def setMagPlotAnnotationFormat(self):
        # somehow its over-riddent after
        mins = min(self.stats[0])
        maxs = min(self.stats[1])
        print(mins, maxs)
#       bound = max(abs(mins), abs(maxs))
#       n = int(log10(bound))
#       ndiff = int(log10(bound))
#       if ndiff > 1:
#           dr = 0
#           total = n
#       else:
#           dr = 3
#           total = n + dr
#       format = "{:" + str(total) + "." + str(dr) + "f}"
        # print("BOUND IS ", bound, "digits left", n,"dr",ndiff)
        # print(format)
#       self.plot_.setYLabelFormat(format)

    def calPlotPoints(self):
        #  determine which section to be plotted
        # error cannot use just self.times (data
        times = self.times
        # print("SEARCH TIMES",self.tO, self.tE)
        iO = timeIndex(times, self.tO, dt=self.resolution)
        iE = timeIndex(times, self.tE, dt=self.resolution) + 1
        if iO is None:
            iO = 0 if self.tO < self.times[0] else None
        if iE is None:
            iO = self.times[-1] if self.tE > self.times[-1] else None
        if iO is None and iE is None:
            print("setTraces: OUT OF BOUNDS")
            start = FFTIME(times[0], Epoch=self.epoch)
            stop_ = FFTIME(times[-1], Epoch=self.epoch)
            Start = FFTIME(self.tO, Epoch=self.epoch)
            Stop_ = FFTIME(self.tE, Epoch=self.epoch)
            print("   Valid ", start.UTC, stop_.UTC)
            print("   Selected ", Start.UTC, Stop_.UTC)
            return
        if (iO == iE):
            start = FFTIME(times[0], Epoch=self.epoch)
            stop_ = FFTIME(times[-1], Epoch=self.epoch)
            Start = FFTIME(self.tO, Epoch=self.epoch)
            Stop_ = FFTIME(self.tE, Epoch=self.epoch)
#           print("ARRAY       ", times[0], times[-1])
            print("   Valid    ", start.UTC, stop_.UTC)
            print("   Selected ", Start.UTC, Stop_.UTC)
            print("NO POINTS IN RANGE ", self.tO, self.tE)
            return
        self.xO = iO
        self.xE = iE

    def setTraces(self):
        index = self.ui.plotTabs.currentIndex()
#       # set the data for plotting here 2016 May 04
#       if index is 0:   #  redo trace for mag GSE
        self.calPlotPoints()
        self.setTrace_(KEY=0)
#       if index is 1:   #  redo trace for mag processed
        if self.proData:
            self.setTrace_(KEY=1)
#       if index is 2:   # redo trace mag BLM
#           print("DO BLM")
#           self.setTrace_(KEY=2)

    def setTrace_(self, KEY=0):  # plot unprocessed data self.plot_
        plots = [self.plot_, self.plotP, self.plotB]
#       print("PRODATA", self.proData)
        if KEY == 1 and self.proData is None:
            return
        if self.proData:
            times = [self.times, self.times, self.times]
            datas = {0: self.magData, 1: self.proData, 2: self.BLMData}
        else:
            times = [self.times, self.times, self.times]
            datas = {0: self.magData, 1: None, 2: self.BLMData}
        plot = plots[KEY]
        data = datas[KEY]
#       print(len(self.magData), len(self.BLMData))
        BLMData = self.BLMData
        flag = self.FID.FFInfo["ERROR_FLAG"].value * .9
        xO = self.xO
        xE = self.xE
        X = times[KEY]
        spaceCraft = where(self.plotSC)[0]
        items = [0, 1, 2, 3]
        for i in spaceCraft:   # spacecraft
            for j in items:            # bx, by, bz, bt
                column = i * 4 + j
                Y = array(data[column])
#               print("column", column, "LEN", len(data), self.ui.plotTabs.currentIndex())
              # print("PLOT ID", j, "SPACE CRAFT", i, len(data[xO:xE]), column)
              # print("BOUNDS", j, min(data[xO:xE]), max(data[xO:xE]))
                if len(Y) > 1:
                    plot.setTrace(j, X[xO:xE], Y[xO:xE], List='y', Flag=flag, SpaceCraft=i)
        # plot current on main panel for debugging
        pIndex = j + 1
        for j in range(4):
            Y = array(data[j])
            if len(Y) > 1:
                plot.setTrace(pIndex, X[xO:xE], Y[xO:xE], List='y', Flag=flag, SpaceCraft=j)
        # plot current on another panel
#       for j in range(3):
#           pIndex = j + 4
#           Y = array(data[j])
#           if len(Y) > 1:
#               plot.setTrace(pIndex, X[xO:xE], Y[xO:xE], List='y', Flag=flag, SpaceCraft=0)

    def setTraceP(self):  # plot unprocessed data self.plot_
        plot = self.plotP
        times = self.times
        flag = self.FID.FFInfo["ERROR_FLAG"].value * .9
        xO = self.xO
        xE = self.xE
        X = times
        spaceCraft = where(self.plotSC)[0]
        items = [0, 1, 2, 3]
        for i in spaceCraft:   # spacecraft
            for j in items:            # bx, by, bz, bt
                column = i * 4 + j
                print(column)
#               data = self.dataP[column]
#               plot.setTrace(j, X[xO:xE], data[xO:xE], List='y', Flag=flag, SpaceCraft=i)

    def mousePressEvent(self, event):
        """ Coordinates in scene not magPlot """
        pass

    # communicators
    # diff between BMag and BPos -> 4 columns vs 3 columns
    #                               self.cols vs self.poss
    # used externally

    def BMag(self, timeO, timeE):
        # print(" BMAG", timeO, timeE)
        cols = self.cols
        flag = self.FID.FFInfo["ERROR_FLAG"].value
        dt = self.FID.getResolution()
        BMAG = sliceByTime(self.times, self.dataByCol, timeO, timeE, cols, dt, flag)
#       print(BMAG.rawData_["bx"][:3])
#       print(BMAG.rawData_["by"][:3])
        BMAG.errorFlag = flag
        return BMAG

    def BPos(self, timeO, timeE):
        cols = self.poss
        flag = self.FID.FFInfo["ERROR_FLAG"].value
        BPOS = sliceByTime(self.times, self.data, timeO, timeE, cols, self.dt, flag)
        return BPOS

    def currentData(self):
        """ returns the current data array """
        data = self.BMag(self.timeO, self.timeE)
        return data

    def statMess(self, mess):
        gv = self.ui.graphicsView
        gv.setStatusTip(mess)

    # disable / enable when there's data
    def _NoData(self):
        """ no data available, frees old data, disables data dependent widgets """
        self.focus = [None] * 4
        self.hodogram = [None] * 4
        self.spectra = [None] * 4
        self.queueDisplay = [None] * 4
#       self.DataCB.setEnabled(False)
        self.ui.statButton.setEnabled(False)
        self.ui.headerButton.setEnabled(False)
        self.ui.dataButton.setEnabled(False)
        self.ui.hodoButton.setEnabled(False)
        self.ui.actionPrint.setEnabled(False)
        self.ui.editButton.setEnabled(False)
        self.ui.spectraButton.setEnabled(False)
        self.ui.focusButton.setEnabled(False)
        self.statDisplay = None
        self.fileDisplay = None
        self.dataDisplay = None

    def _reset(self):
        DIALOG(self, "RESET")
        self._ResetData()

    def _ResetData(self):
        """
        new data has been read, clear out any data dependent panels
        :return:n
        """
        # clear out any intervals
        self.refreshMagPlot()

    def _HasData(self):
        """ data available, enables data dependent widgets """
#       self.ui.actionFocus.setEnabled(True)
#       self.ui.actionHodogram.setEnabled(True)
        self.ui.statButton.setEnabled(True)
        self.ui.headerButton.setEnabled(True)
        self.ui.dataButton.setEnabled(True)
        self.ui.hodoButton.setEnabled(True)
        self.ui.focusButton.setEnabled(True)
        self.ui.editButton.setEnabled(True)
        self.ui.spectraButton.setEnabled(True)
#       self.ui.actionHeader.setEnabled(True)
#       self.ui.actionData.setEnabled(True)
#       self.ui.actionStat.setEnabled(True)
        self.ui.actionPrint.setEnabled(True)

    # batch functions
    def processArgs(self):
        """ process command options here """
        if self.argProcess:
            return
#       print("    processArgs", sys.argv)
        key = "numpoints="
        numList = any(key in item for item in sys.argv)
        if numList:
            numPairs = [x for x in sys.argv if key in x]
            numPair = numPairs[0]
            pos = numPair.index('=') + 1
            numStr = numPair[pos:]
            FFMag.ARGPOINTS = int(numStr) if numStr.isdigit() else 500000
            self.numpoints = FFMag.ARGPOINTS
        key = "path="
        pathList = any(key in item for item in sys.argv)
        if pathList:
            pathPair = numPairs[0]
            pos = pathPair.index('=') + 1
            pathStr = pathPair[pos:]
            FFMag.LAST_PATH = pathStr
        self.argProcess = True

    def presets(self):
        """ load presets"""
        name = self.name
        self.settings = settings = QSettings(name + '.ini', QSettings.IniFormat)
        # File only, not registry or or.
        settings.setFallbacksEnabled(False)
        settings.setPath(QSettings.IniFormat, QSettings.SystemScope, './__settings.ini')
        pos = QtCore.QPoint(0, 0)
        state = self.saveState()
        self.move(self.settings.value('MainWindow/Position', pos))
        self.restoreState(self.settings.value('MainWindow/State', state))
        self.genPlotControls()
        self.setEditActions()
        self.ui.printPanel.clicked.connect(self.printPanel)
        self._NoData()  # no file read yet

    def NOTYET(self):
        DIALOG(self, "NOT YET IMPLEMENTED")

    def selectPrompt(self, label):
        self.ui.statusbar.showMessage(label + ":Select interval on plot")
        self.ui.magView.setStatusTip("Left Click for " + label)


def homeDir():
    home = expanduser("~")
    return home


def currDate(iformat=0):
    format = ["yyyy MMM dd",  "yyyy MM dd"]
    qDate = QtCore.QDate.currentDate()
    return qDate.toString(format[iformat])

if __name__ == "__main__":
    appName = "MMSMag"
    app = QApplication(sys.argv)
    app.setOrganizationName("IGPP/UCLA")
    app.setOrganizationDomain("igpp.ucla.edu")
    app.setApplicationName(appName)
    size = preAmble(app, Icon="magPy.png")
    file = None
    args = processArgs(sys.argv, ["css", "file"])
    confDict = config("FFMMSMag.cfg")   # default configuration file
    if args:
        if args["file"]:
            file = args["file"]
        if args["config"]:
            configFile = args["config"]
            confDict = config(configFile)
    if not file and "MMSFILE" in confDict.keys():
        file = confDict["MMSFILE"]
#       print("INPUT IS", input())
#       print("CONFIGDICT", confDict)
    input = file
    myApp = FFMag(name=appName, title=appName, batch=False, file=input,
                  maxGeometry=size, config=confDict)
    lFile = leapFile()
    if os.path.isfile(lFile) is None:
        DIALOG(myApp, "Leap Table " + lFile + " not Found.")
        quit()
    args = processArgs(sys.argv, ["css", "develop"])
    if args:
        if args["css"]:
            setStyleSheet(myApp, args["css"])
    myApp.show()
    sys.exit(app.exec_())
