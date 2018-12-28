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

class OWNxEpsilonGraph(widget.OWWidget):
    name = "Proximity Graph Generator"
    description = ('Constructs Graph object from distance matrix')
    icon = "icons/NetworkProximityGraphs.svg"
    priority = 6440 #priority based on NetworkFromDistances widget

    class Inputs:
        distances = Input("Distances", DistMatrix)

    class Output:
        network = Output("Network", network.Graph)
        data = Output("Data", Table)
        distances = Output("Distances", DistMatrix)

    resizing_enabled = False

    def __init__(self):
        super().__init__()

        self.matrix = None
        self.graph = None
        self.graph_matrix = None

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

        # Magnitude of the spinbox's step is data-dependent
        low, upp = values[0], values[-1]
        step = (upp - low) / 20
        self.spin_high.setSingleStep(step)

        self.spinUpperThreshold = low - (0.03 * (upp - low))

        self.setPercentil()
        self.generateGraph()

if __name__ == "__main__":
    from AnyQt.QtWidgets import QApplication
    appl = QApplication([])
    ow = OWNxEpsilonGraph()
    ow.show()
    appl.exec_()
