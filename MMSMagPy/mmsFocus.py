# leel 2016 Jul 22 special focus plot for mms data
from bxUtil import focusPlot
from FF_File import timeIndex
from plot import Pen


class mmsFocus(focusPlot):
    def __init__(self, parent=None, data=None):
        print("INIT mmsFocus")
        self.spaceCraft = [0, 1, 2, 3]
        self.pens = [Pen.Blue, Pen.Green, Pen.Magenta, Pen.BUFF]
        focusPlot.__init__(self, parent=parent, data=data)

    def setPens(self, pens):
        self.pens = pens

    def setTraces(self):
        print("    mmmsFocus:setTraces")
        times = self.data.times
        flag = self.data.FID.FFInfo["ERROR_FLAG"].value
        xO = timeIndex(times, self.tO)
        xE = timeIndex(times, self.tE)
        graphs = self.plot.graphs
        base = "MMS"
        subBase = ["X", "Y", "Z", "T"]
        sList = ""
        for sc in self.spaceCraft:
            sList += str(sc + 1)
        for p in range(4):   # bx, by, bz, bt plots
            label = base + subBase[p] + sList
            graphs[p].right.setTitle(label)
        for sc in self.spaceCraft:
            columns = [(sc - 1) * 8 + j for j in range(4)]  # bx, by, bz, bt
            pen = self.pens[sc - 1]
            for p in range(4):   # bx, by, bz, bt plots
                data = self.data.data[columns[p]]
                self.plot.setTrace(p, times[xO:xE], data[xO:xE],
                                   List='y', Flag=flag, Pen=pen)

    def setSpaceCraft(self, sc):
        self.spaceCraft = sc
        self.refresh()
