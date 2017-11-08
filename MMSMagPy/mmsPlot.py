# components
#    magPlot (pos, size)
#
# 2014 jan 31 - support multiple intervals and labeling intervals
#  interval -> start, stop, pen, label
from copy import deepcopy
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QFont, QFontMetrics, QGraphicsItem
from PyQt4.QtCore import QPointF
from PyQt4.QtCore import QSizeF
from PyQt4.QtGui import QStaticText as QText
from FF_Time import FFTIME
from magPlot import interval
from graph import Graph
from axis import Axis
from plot import Pen
from bestformat import formatNumber

class MMSPlot(QGraphicsItem):
    """ 7 graph display """

    MARGIN = 50
    Pens = [Pen.Blue, Pen.Green, Pen.Magenta, Pen.BUFF]

    def __init__(self, pos, size, bounds,
                 HeaderLeft=None, Header=None, HeaderRight=None,
                 FooterLeft=None, Footer=None, FooterRight=None,
                 Title="title", Legend=False, Frame=False):
        super(MMSPlot, self).__init__()
        if type(pos) is not QPointF:
            pos = QtCore.QPointF(pos)
        if type(size) is not QSizeF:
            size = QtCore.QSizeF(size)
        self.pos = pos            # (x,y) bottom left corner plot (device coords)
        self.size = size          # (width, height) of plot
#       print("INIT SIZE",size)
        self.bounds = bounds      # ((Xo, Yo),(width, Height) plot coordinate system
        self.title = Title        # graph title  not implemented
        self.hLeft = HeaderLeft   # text above graph (left, right)
        self.hCent = Header       # text above graph (left, right)
        self.hRigh = HeaderRight  # text above graph (left, right)
        self.fLeft = FooterLeft   # text below graph (left, right)
        self.fCent = Footer       # text below graph (left, right)
        self.fRigh = FooterRight  # text below graph (left, right)
        self.frame = Frame
        self.legend = Legend   # not implemented
        # event processing attributes
        self.ninterval = 0   # number intervals
        self.cinterval = 0   # current interval
        self.intervals = []  # interval list
        self.interval = None  # interval list
        self.go = False
        self.count = 0
        self.selection = []
        self.timeSeg = []
        height = size.height()
        self.setPos(pos)
        self.setGeometry()
        s = QtCore.QSizeF(size)
        dy = height / 9.5
        s.setHeight(dy)
        s.setWidth(size.width()- 2 * MMSPlot.MARGIN)
        xOff = float(MMSPlot.MARGIN)
        yOff = -height + MMSPlot.MARGIN
        border = Graph.RIGHT | Graph.LEFT | Graph.TOP
        gpos = QtCore.QPointF(xOff,  dy + yOff)
        self.bx = Graph(gpos, s, bounds,
                        RightLabel="Bx", Type=Graph.TY,
                        Borders=border, LabelLimit=(0, 0, 2), Base=0)
        self.bx.top.label = Axis.NOLABEL
        self.bx.top.labels = None
        self.bx.top.title = None
#       self.bx.grid.setTracePen(Pen.Blue)
        border = Graph.RIGHT | Graph.LEFT
        gpos = QtCore.QPointF(xOff, yOff + 2 * dy)
        self.by = Graph(gpos, s, bounds,
                        RightLabel="By", Type=Graph.TY,
                        Borders=border, LabelLimit=(0, 1, 2), Base=0)
#       self.by.grid.setTracePen(Pen.Green)
        gpos = QtCore.QPointF(xOff, yOff + 3 * dy)
        self.bz = Graph(gpos, s, bounds,
                        RightLabel="Bz", Type=Graph.TY,
                        Borders=border, LabelLimit=(0, 1, 2), Base=0)
#       self.bz.grid.setTracePen(Pen.Cyan)
        gpos = QtCore.QPointF(xOff, yOff + 4 * dy)
#       border = Graph.RIGHT | Graph.LEFT
        self.bt = Graph(gpos, s, bounds,
                        RightLabel="Bt", Type=Graph.TY,
                        Borders=border, LabelLimit=(0, 1, 2), Base=0)
#       self.bt.grid.setTracePen(Pen.Red)
        gpos = QtCore.QPointF(xOff, yOff + 5 * dy)
        self.i = Graph(gpos, s, bounds,
                        RightLabel="i", Type=Graph.TY,
                        Borders=border, LabelLimit=(0, 1, 2), Base=0)
        gpos = QtCore.QPointF(xOff, yOff + 6 * dy)
        self.j = Graph(gpos, s, bounds,
                        RightLabel="j", Type=Graph.TY,
                        Borders=border, LabelLimit=(0, 1, 2), Base=0)
        gpos = QtCore.QPointF(xOff, yOff + 7 * dy)
        border = Graph.RIGHT | Graph.LEFT | Graph.BOTTOM
        self.k = Graph(gpos, s, bounds,
                        RightLabel="k", Type=Graph.TY,
                        Borders=border, LabelLimit=(0, 1, 2), Base=None)
        self.graphs = [self.bx, self.by, self.bz, self.bt, self.i, self.j, self.k]
        for g in self.graphs:
            g.right.labels = None
            g.right.label = Axis.NOLABEL
            g.setParentItem(self)
            g.left.tic = (0, -.5, 0)
            g.right.tic = (0, .5, 0)
            g.left.setUserHorizontalOffset(10)
#       for i in range(4):
#           self.graphs[i].left.tic = (0, .5, 0)
#           self.graphs[i].right.tic = (.5, 0, 0)
        self.selectColor = Pen.Red
        # for extracting intervals, selection
#       scene = QGraphicsScene(self.brect)
#       print("SCENE SIZE", scene)
#       self.setSelected(False)
#       print("   GRAPHICS SCENE", self.scene())
#       print("   GRAPHICS SCENE", self.sceneBoundingRect())
#       print("   GRAPHICS SCENE", self.scenePos())
#       self.mousePressEvent = self.mousePressEventInterval

    def boundingRect(self):
        M = MMSPlot.MARGIN
        MY = 8 * M
        MX = 4 * M
        return self.frect.adjusted(-MX, MY, MX, -MY)

    def setGeometry(self):
        OFF = MMSPlot.MARGIN
        zero = QtCore.QPointF(0, 0)
        off = QtCore.QPointF(-Graph.MARGIN, Graph.MARGIN)
        width = self.size.width()
        height = self.size.height()
        gsize = QtCore.QSizeF(width + 2 * Graph.MARGIN, -(height + 2 * Graph.MARGIN))
        fsize = QtCore.QSizeF(width, -height)
        self.frect = QtCore.QRectF(zero, fsize).adjusted(-OFF, OFF, OFF, -OFF)
        self.prect = QtCore.QRectF(zero, fsize)
        self.gFrame = QtCore.QRectF(off, gsize)
        self.geometry = QtCore.QRectF(zero, self.size)
        gsize = QtCore.QSizeF(width + Graph.MARGIN, height)
        self.brect = self.geometry
        self.brect = QtCore.QRectF(zero, gsize)

    def setAxis(axis, adjust, Time=False):
        """ sets axii attributes LINEAR/LOG, LABELING, LABEL FORMAT, TITLE"""
        pass

    def drawFrame(self, painter):
        painter.drawRect(self.frect)  # graph bounds

    def charSize(self):
        font = QFont()
        fm = QFontMetrics(font)
        off = fm.height()
        return off

    def paintTextRight(painter, string, x, y):
        font = QFont()
        fm = QFontMetrics(font)
        off = fm.height()
        text = QText(string)
        xo = x - len(string) * off / 2
        pos = QPointF(xo, y)
        painter.drawStaticText(pos, text)

    def paintTextCenter(painter, string, x, y):
        font = QFont()
        fm = QFontMetrics(font)
        off = fm.height()
        text = QText(string)
        xo = x - len(string) * off / 2
        pos = QPointF(xo, y)
        painter.drawStaticText(pos, text)

    def PaintSelection(self, painter, option):
        top = self.prect.top()
        bottom = self.prect.bottom()
        painter.setPen(self.selectColor)
#       if self.mousePressEvent is self.mousePressEventInterval:
#           print("OLD")
#       else:
#           print("NEW")
        for x in self.selection:
            painter.drawLine(x, top, x, bottom)

    def paintSelection(self, painter, option):
        if self.count == 0:
            return
        top = self.prect.top()
        bottom = self.prect.bottom()
        segs = self.interval.segs
#       print("SELF INTERVAL", self.interval.__dict__)
#       print("SELECT", segs, len(segs))
        for i in range(self.interval.size):
#           print("I ", i, "current", self.interval.current)
##          if i > self.interval.current:
#               print("PASS drawSelection")
##              pass
#           print("DO ", i, segs[i].pen.__dict__)
            for x in segs[i].selection:
#               print("I", i, "X", x, segs[i].label, segs[i].pen.color)
                painter.setPen(segs[i].pen)
                if x == interval.FLAG:
                    pass
                painter.drawLine(x, top, x, bottom)
                pos = QPointF(x, bottom)
                if segs[i].label:
                    qFont = QFont()
                    qM = QFontMetrics(qFont)
                    off = qM.width(segs[i].label) / 2
                    pos.setX(x - off)
                    painter.drawStaticText(pos, QText(segs[i].label))
#       for selection in self.interval.selection:
#           print(selection)
#           for x in selection:
#               painter.drawLine(x, top, x, bottom)

    def paint(self, painter, option, widget=None):
#       painter.fillRect(option.rect, QtCore.Qt.green)
#       self.drawFrame(painter)
        m = Graph.MARGIN
        m = 0
        w = self.size.width()
        x = -m
        y = -self.size.height() - m
        if self.hLeft:
            text = QText(self.hLeft)
            pos = QPointF(0, y)
            painter.drawStaticText(pos, text)
        if self.hCent:
            MMSPlot.paintTextCenter(painter, self.hCent, x + w / 2, y)
        if self.hRigh:
            MMSPlot.paintTextRight(painter, self.hRigh, x + w, y)
        y  = -self.charSize() * 3
        if self.fLeft:
            text = QText(self.fLeft)
            pos = QPointF(0, y)
            painter.drawStaticText(pos, text)
        if self.fCent:
            MMSPlot.paintTextCenter(painter, self.fCent, x + w / 2, y)
        if self.fRigh:
            MMSPlot.paintTextRight(painter, self.fRigh, x + w, y)
        if self.interval is not None:
            self.paintSelection(painter, option)

    def resetBounds(self, plotParms, BLMParms, times):
        """ reset plot bounds """
        # plotParms  (scale, above, below)
        # span (tO, tE, epoch) in offsets
        graphs = self.graphs
        tO = times[0]
        tE = times[1]
        self.epoch = epoch = times[2]
        # adjust only bx top and bt bottom time axis
        self.bx.top.resetTimes((tO, tE), epoch)
        self.bx.top.setTitle(None)
        self.k.bottom.resetTimes((tO, tE), epoch)
        for i in range(7):  # adjust bx, by, bz, bt
            if i < 4 :
                scale = plotParms[0]
                above = plotParms[1]
                below = plotParms[2]
                index = i
            else:
                scale = BLMParms[0]
                above = BLMParms[1]
                below = BLMParms[2]
                index = i - 4
            a = above[index]
            b = below[index]
            yO = -scale * b
            yE = scale * a
            bounds = (yO, yE, scale, 0)
            inter = graphs[i].left.labelBounds[2]  # major tics per label
            form = formatNumber(scale * inter, Signed=(yO * yE < 0))
            if i != 3:
                off = 2
            else:
                off = 0
            if yO % 2 == 0:
                graphs[i].left.limitLabels(start=off, stop=1)
                graphs[i].right.limitLabels(start=off + 1, stop=1)
            else:
                graphs[i].left.limitLabels(start=1, stop=1)
                graphs[i].right.limitLabels(start=1, stop=1)
            # graph vertical axii
            graphs[i].setYBounds(bounds)
            graphs[i].left.setFormat(form)
            # set grid coords
            po = QtCore.QPointF(tO, yO)
            pe = QtCore.QPointF(tE, yE)
            graphs[i].grid.resetWorldCoordinates(po, pe)
#       for i in range(0, 4):
#           xO, yO, xE, yE = graphs[i].grid.WorldCoordinates()
#           po = QtCore.QPointF(tO, yO)
#           pe = QtCore.QPointF(tE, yE)
#           print("Reset Grid", i)
#           graphs[i].grid.resetWorldCoordinates(po, pe)

    def setTrace(self, PlotId, X, Y, Flag=None, List=None, SpaceCraft=0):
#       print("set trace", type(X), type(Y), List, Y[:3])
#       print("PLOTID", PlotId, SpaceCraft, len(MMSPlot.Pens))
#       self.graphs[PlotId].addTrace(X, Y, List=List, Flag=Flag)
        self.graphs[PlotId].addTrace(X, Y, List=List, Flag=Flag, Pen=MMSPlot.Pens[SpaceCraft])
#       if PlotId == 3:
#           print(self.graphs[3].traces[0])

    def clear(self):
        for i in range(4):
            self.graphs[i].SEGS = None
            self.graphs[i].GAPS = None
            self.graphs[i].filter = None
            self.graphs[i].traces = []
            self.graphs[i].ntrace = 0
            self.graphs[i].clear()

    def MousePressEvent(self, event):
#       if not self.focus:
#           event.ignore()
#           return
#       print("MOUSE PRESS EVENT ONE")
        if self.count >= 2:
            event.ignore()
        if self.count == 1:
            self.secondTime(event)
#           event.ignore()
        if self.count == 0:
            self.firstTime(event)
#           self.focus = False
            event.ignore()

    def setInterval(self, interval):
        self.interval = interval

    def setClient(self, client, SWITCH=None):
        #  client requires interval (class intervals), focusSlot
        print("SET CLIENT", client)
        self.client = client
        self.interval = client.interval
        self.setMousePressEvent(SWITCH=SWITCH)

    def setClientInterval(self, client, interval, SWITCH=None):
        #  client requires interval (class intervals), focusSlot
        self.client = client
        self.interval = interval
        self.setMousePressEvent(SWITCH=SWITCH)

    def resetSelections(self):
        """ empties selection/time lists """
        """ client contains intervals instance, for magPlot to manipulate"""
#       self.interval = self.client.interval
        self.selection = []
        self.timeSeg = []
        self.count = 0
        self.go = True

    def selectTime(self, event):  # obtain mouse positions, set timeSeg
        x = event.pos().x()
        self.selection.append(x)
        t = self.bt.bottom.pos2Time(x)
        self.timeSeg.append(t)
        return t

    def time2Selection(self, i):  # sets positions from the timeSeg
        interval = self.interval
        tO, t1 = interval.segs[i].timeSeg
        xO = self.bt.bottom.time2Pos(tO)
        x1 = self.bt.bottom.time2Pos(t1)
        interval.segs[i].selection = [xO, x1]

    def UTC2Selection(self, i, UTCO, UTC1):  # UTC to selections and timeSeg
        interval = self.interval
        tO = FFTIME(UTCO, Epoch=self.epoch)
        t1 = FFTIME(UTC1, Epoch=self.epoch)
        interval.segs[i].timeSeg = [tO, t1]
        xO = self.bt.bottom.time2Pos(tO)
        x1 = self.bt.bottom.time2Pos(t1)
        interval.segs[i].selection = [xO, x1]
        self.count = self.count + 1

    def setMousePressEvent(self, SWITCH='I'):
        if SWITCH is None:
            self.mousePressEvent = self.mousePressEventInterval
            return
        if SWITCH is 'I':
            self.mousePressEvent = self.mousePressEventInterval
            return
        self.mousePressEvent = self.mousePressEventSelect

    def SceneEvent(self, event):
        print("SSGPLOT SCENE EVENT")
        event.ignore()
        return True

    def mousePressEventSelect(self, event):
        self.count = self.count + 1
        if not self.go:
            event.ignore()
            return
        if self.count < 2:
            x = event.pos().x()
            self.selection.append(x)
            t = self.bt.bottom.pos2Time(x)
            self.timeSeg.append(t)
            interval = self.interval
            i = interval.current
            interval.segs[i].timeSeg = self.timeSeg
            interval.segs[i].selection = self.selection
            widget = event.widget()
            widget.repaint(0, 0, self.size.width(), self.size.height() * 3)
            event.accept()
            if self.count > 0:
                self.go = False
                if i < interval.size:
#                   interval.timeSeg[i] = self.timeSeg
#                   interval.selection[i] = self.selection
                    interval.current += 1
                    self.client.focusSlot()
        self.prepareGeometryChange()

    def mousePressEventInterval(self, event):
        """ aka mousePressSelect: will override main """
        self.count = self.count + 1
        if not self.go:
#           print("    SSGPLOT MOUSEPRESS ignore", event.pos())
            event.ignore()
            return
        if self.count < 3:
#           print("    SSGPLOT MOUSEPRESS process", event.pos())
            x = event.pos().x()
            self.selection.append(x)
            t = self.bt.bottom.pos2Time(x)
            self.timeSeg.append(t)
            interval = self.interval
            i = interval.current
            interval.segs[i].timeSeg = self.timeSeg
            interval.segs[i].selection = self.selection
            widget = event.widget()
            widget.repaint(0, 0, self.size.width(), self.size.height() * 3)
            event.accept()
            if self.count > 1:
                self.go = False
                if i < interval.size:
#                   interval.timeSeg[i] = self.timeSeg
#                   interval.selection[i] = self.selection
                    interval.current += 1
                    self.client.focusSlot()
        self.prepareGeometryChange()
        return

    def setMinMaxTic(self, ymin, ymax, tic, times, pretty=True):
        tO = times[0]
        tE = times[1]
        graphs = self.graphs
        for i in range(4):  # adjust bx, by, bz, bt
            yO = ymin[i]
            yE = ymax[i]
            scale = tic[i]
            bounds = (yO, yE, scale, 0)
#           inter = graphs[i].left.labelBounds[2]  # major tics per label
            inter = 1
            form = formatNumber(scale * inter)
            if pretty:
                if i != 3:
                    off = 2
                else:
                    off = 0
                if yO % 2 == 0:
                    graphs[i].left.limitLabels(start=off, stop=0)
                    graphs[i].right.limitLabels(start=off, stop=0)
                else:
                    graphs[i].left.limitLabels(start=1, stop=0)
                    graphs[i].right.limitLabels(start=1, stop=0)
            else:
                graphs[i].left.limitLabels(start=0, stop=0)
                graphs[i].right.limitLabels(start=0, stop=0)

            # graph vertical axii
            graphs[i].setYBounds(bounds)
            # print("magPlot.py:FORM IS ", form)
            graphs[i].left.setFormat(form)
            # set grid coords
            po = QtCore.QPointF(tO, yO)
            pe = QtCore.QPointF(tE, yE)
            graphs[i].grid.resetWorldCoordinates(po, pe)

    def setInteveralColor(self, color):
        self.selectColor = color

    def setYLabelFormat(self, format):
        graphs = self.graphs
        for i in range(4):
            graphs[i].left.setFormat(format)
            graphs[i].right.setFormat(format)

    def setYLabels(self, yLabel):   # set Y labels on axii
        pass

    def pens(self):
        return MMSPlot.Pens
