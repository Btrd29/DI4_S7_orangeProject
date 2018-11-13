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

class OWNxProximityGraphs(widget.OWWidget):
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
