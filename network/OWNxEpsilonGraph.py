# Widget for proximity graphs
#
# Authors - Benoît Richard - Thomas Rossi
# Created on 2018-11-08

import numpy as np

from AnyQt.QtCore import QLineF, QSize

from Orange.data import Domain, StringVariable, Table
from Orange.misc import DistMatrix
from Orange.widgets import gui, widget, settings
from Orange.widgets.widget import Input, Output
import orangecontrib.network as network

import pyqtgraph as pg # lib for graphs, used for Histogram

class OWNxEpsilonGraph(widget.OWWidget):
    name = "Epsilon Proximity Graph Generator"
    description = ('Constructs Graph object using Epsilon algorithm. '
                   'Nodes from data table are connected only if the '
                   'distance between them is equal or less than a '
                   'given parameter (ε).')
    icon = "icons/EpsilonNetworkProximityGraph.svg"
    priority = 6440 #priority based on NetworkFromDistances widget

    class Inputs:
        distances = Input("Distances", DistMatrix)

    class Outputs:
        network = Output("Network", network.Graph)
        data = Output("Data", Table)
        distances = Output("Distances", DistMatrix)

    resizing_enabled = False

    class Warning(widget.OWWidget.Warning):
        large_number_of_nodes = widget.Msg('Large number of nodes/edges; performance will be hindered')

    class Error(widget.OWWidget.Error):
        number_of_edges = widget.Msg('Estimated number of edges is too high ({})')

    def __init__(self):
        super().__init__()

        self.epsilon = 0

        self.matrix = None
        self.graph = None
        self.graph_matrix = None

        self.histogram = Histogram(self)
        self.mainArea.layout().addWidget(self.histogram)
        self.mainArea.setMinimumWidth(500)
        self.mainArea.setMinimumHeight(100)
        self.addHistogramControls()

        # info
        boxInfo = gui.widgetBox(self.controlArea, box="Info")
        self.infoa = gui.widgetLabel(boxInfo, "No data loaded.")
        self.infob = gui.widgetLabel(boxInfo, '')
        self.infoc = gui.widgetLabel(boxInfo, '')

        gui.rubber(self.controlArea)

        self.resize(600, 400)

    def addHistogramControls(self):
        boxHisto = gui.widgetBox(self.controlArea, box="Algorithm controls")
        ribg = gui.widgetBox(boxHisto, None, orientation="horizontal", addSpace=False)
        self.spin_high = gui.doubleSpin(boxHisto, self, 'epsilon',
                                        0, float('inf'), 0.001, decimals=3,
                                        label='Epsilon',
                                        callback=self.changeUpperSpin,
                                        keyboardTracking=False,
                                        controlWidth=60)
        self.histogram.region.sigRegionChangeFinished.connect(self.spinboxFromHistogramRegion)

    # Processing distance input
    @Inputs.distances
    def set_matrix(self, data):
        self.matrix = data
        if data is None:
            self.histogram.setValues([])
            self.generateGraph()
            return

        if self.matrix.row_items is None:
            self.matrix.row_items = list(range(self.matrix.shape[0]))

        # draw histogram
        self.matrix_values = values = sorted(self.matrix.flat)
        self.histogram.setValues(values)

        self.generateGraph()

    def generateGraph(self, N_changed=False):
        self.Error.clear()
        self.Warning.clear()
        matrix = None

        if N_changed:
            self.node_selection = NodeSelection.COMPONENTS

        if self.matrix is None:
            if hasattr(self, "infoa"):
                self.infoa.setText("No data loaded.")
            if hasattr(self, "infob"):
                self.infob.setText("")
            if hasattr(self, "infoc"):
                self.infoc.setText("")
            self.pconnected = 0
            self.nedges = 0
            self.graph = None
            self.sendSignals()
            return

        nEdgesEstimate = 2 * sum(y for x, y in zip(self.histogram.xData, self.histogram.yData)
                                 if x <= self.epsilon)

        if nEdgesEstimate > 200000:
            self.graph = None
            nedges = 0
            n = 0
            self.Error.number_of_edges(nEdgesEstimate)
        else:
            graph = network.Graph()
            graph.add_nodes_from(range(self.matrix.shape[0]))
            matrix = self.matrix

            if matrix is not None and matrix.row_items is not None:
                if isinstance(self.matrix.row_items, Table):
                    graph.set_items(self.matrix.row_items)
                else:
                    data = [[str(x)] for x in self.matrix.row_items]
                    items = Table(Domain([], metas=[StringVariable('label')]), data)
                    graph.set_items(items)

            def edges_via_epsilon(matrix, epsilon):
                rows, cols = matrix.shape
                for i in range(rows):
                    for j in range(i + 1, cols):
                        if matrix[i, j] <= epsilon:
                            yield i, j, matrix[i, j]

            edges = edges_via_epsilon(self.matrix, self.epsilon)
            graph.add_edges_from((u, v, {'weight': d}) for u, v, d in edges)
            matrix = None
            self.graph = None
            component = []
            self.graph = graph
            if len(component) > 1:
                if len(component) == graph.number_of_nodes():
                    self.graph = graph
                    matrix = self.matrix
                else:
                    self.graph = graph.subgraph(component)
                    matrix = self.matrix.submatrix(sorted(component))

        if matrix is not None:
            matrix.row_items = self.graph.items()
        self.graph_matrix = matrix

        if self.graph is None:
            self.pconnected = 0
            self.nedges = 0
        else:
            self.pconnected = self.graph.number_of_nodes()
            self.nedges = self.graph.number_of_edges()
        if hasattr(self, "infoa"):
            self.infoa.setText("Data items on input: %d" % self.matrix.shape[0])
        if hasattr(self, "infob"):
            self.infob.setText("Network nodes: %d (%3.1f%%)" % (self.pconnected,
                self.pconnected / float(self.matrix.shape[0]) * 100))
        if hasattr(self, "infoc"):
            self.infoc.setText("Network edges: %d (%.2f edges/node)" % (
                self.nedges, self.nedges / float(self.pconnected)
                if self.pconnected else 0))

        self.Warning.large_number_of_nodes.clear()
        if self.pconnected > 1000 or self.nedges > 2000:
            self.Warning.large_number_of_nodes()

        self.sendSignals()
        self.histogram.setRegion(0, self.epsilon)

    # Outputs processing (has to be called if any modification on the network happens)
    def sendSignals(self):
        self.Outputs.network.send(self.graph)
        self.Outputs.distances.send(self.graph_matrix)
        if self.graph is None:
            self.Outputs.data.send(None)
        else:
            self.Outputs.data.send(self.graph.items())

    def changeUpperSpin(self):
        if self.matrix is None: return
        self.epsilon = np.clip(self.epsilon, *self.histogram.boundary())
        self.percentil = 100 * np.searchsorted(self.matrix_values, self.epsilon) / len(self.matrix_values)
        self.generateGraph()

    def spinboxFromHistogramRegion(self):
        _, self.epsilon = self.histogram.getRegion()
        self.changeUpperSpin()

# Dependencies (InfiniteLine & Histogram)
pg_InfiniteLine = pg.InfiniteLine
class InfiniteLine(pg_InfiniteLine):
    def paint(self, p, *args):
        # From orange3-bioinformatics:OWFeatureSelection.py, thanks to @ales-erjavec
        brect = self.boundingRect()
        c = brect.center()
        line = QLineF(brect.left(), c.y(), brect.right(), c.y())
        t = p.transform()
        line = t.map(line)
        p.save()
        p.resetTransform()
        p.setPen(self.currentPen)
        p.drawLine(line)
        p.restore()

# Patched so that the Histogram's LinearRegionItem works on MacOS
pg.InfiniteLine = InfiniteLine
pg.graphicsItems.LinearRegionItem.InfiniteLine = InfiniteLine


class Histogram(pg.PlotWidget):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, setAspectLocked=True, **kwargs)
        self.curve = self.plot([0, 1], [0], pen=pg.mkPen('b', width=2), stepMode=True)
        self.region = pg.LinearRegionItem([0, 0], brush=pg.mkBrush('#02f1'), movable=True)
        self.region.sigRegionChanged.connect(self._update_region)
        # Selected region is only open-ended on the the upper side
        self.region.hoverEvent = self.region.mouseDragEvent = lambda *args: None
        self.region.lines[0].setVisible(False)
        self.addItem(self.region)
        self.fillCurve = self.plotItem.plot([0, 1], [0],
            fillLevel=0, pen=pg.mkPen('b', width=2), brush='#02f3', stepMode=True)
        self.plotItem.vb.setMouseEnabled(x=False, y=False)

    def _update_region(self, region):
        rlow, rhigh = self.getRegion()
        low = max(0, np.searchsorted(self.xData, rlow, side='right') - 1)
        high = np.searchsorted(self.xData, rhigh, side='right')
        if high - low > 0:
            xData = self.xData[low:high + 1].copy()
            xData[0] = rlow  # set visible boundaries to match region lines
            xData[-1] = rhigh
            self.fillCurve.setData(xData, self.yData[low:high])

    def setBoundary(self, low, high):
        self.region.setBounds((low, high))

    def boundary(self):
        return self.xData[[0, -1]]

    def setRegion(self, low, high):
        low, high = np.clip([low, high], *self.boundary())
        self.region.setRegion((low, high))

    def getRegion(self):
        return self.region.getRegion()

    def setValues(self, values):
        self.fillCurve.setData([0,1], [0])
        if not len(values):
            self.curve.setData([0, 1], [0])
            self.setBoundary(0, 0)
            return
        nbins = int(min(np.sqrt(len(values)), 100))
        freq, edges = np.histogram(values, bins=nbins)
        self.curve.setData(edges, freq)
        self.setBoundary(edges[0], edges[-1])
        self.autoRange()

    @property
    def xData(self):
        return self.curve.xData

    @property
    def yData(self):
        return self.curve.yData

# main class
if __name__ == "__main__":
    from AnyQt.QtWidgets import QApplication
    a = QApplication([])
    ow = OWNxEpsilonGraph()
    ow.show()
    a.exec_()
