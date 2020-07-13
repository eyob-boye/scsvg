import sys
import os
import collections
import time
from PySide2 import QtCore
from PySide2.QtWidgets import QApplication, QHBoxLayout, QSizePolicy, QWidget, QTableWidget, QTableWidgetItem, QMainWindow

# Some pathes needed for locating import from relative path.
THIS_SCRIPT_LOCATION = os.path.dirname(__file__)
SCSVG_LOCATION = os.path.join(THIS_SCRIPT_LOCATION, "../..")
sys.path.append(SCSVG_LOCATION)

import scsvg

class DataItem(QTableWidgetItem):
    def __init__(self, rown=0, coln=0, parent=None):
        super(DataItem, self).__init__(parent)
        self.rown = rown
        self.coln = coln
        self.values = []

class TrafficLight_SC(QMainWindow):
    """
    """
    def __init__(self, parent=None):
        super(TrafficLight_SC, self).__init__(parent)

        self.context = collections.OrderedDict([
            ("__builtins__", {}),
            ("after_20_sec",False),
            ("after_5_sec",False),
            ("hardware_failure",False)
        ])

        self.row_titles = ["SampleTime"] + [k for k in self.context.keys()]
        self.n_rows = len(self.row_titles)
        self.n_cols = 1

        self.sv_table = QTableWidget()
        self.sv_table.setObjectName("sv_table")
        self.sv_table.setRowCount(self.n_rows)
        self.sv_table.setColumnCount(self.n_cols)
        for rown, r in enumerate(self.row_titles):
            item = QTableWidgetItem("%s" % r)
            self.sv_table.setVerticalHeaderItem(rown, item)

        self.data_items = {}
        data_item = DataItem(rown=0, coln=0)
        self.data_items[(0,0)] = data_item
        self.sv_table.setItem(0, 0, data_item)
        # Then iterate through the monitored data items.
        for coln in range(self.n_cols):
            for rown in range(self.n_rows)[1:]:
                data_item = DataItem(rown=rown, coln=coln)
                self.data_items[(rown,coln)] = data_item
                data_item.setText("%s" % self.context[self.row_titles[rown]])
                self.sv_table.setItem(rown, coln, data_item)

        self.setCentralWidget(self.sv_table)

        self.t_start = time.time()

        # Set the data polling timer.
        self.timer = QtCore.QTimer(self)
        self.connect(self.timer, QtCore.SIGNAL("timeout()"), self.update_ui)
        self.timer.start(2000)


    def update_ui(self):
        t_data = (time.time() - self.t_start)
        print(t_data)
        # Save the data time first
        data_item = self.data_items[(0, 0)]
        data_item.setText("%10.1f" % t_data)

        for coln in range(self.n_cols):
            for rown in range(self.n_rows)[1:]:
                data_item = self.data_items[(rown, coln)]
                val_t = data_item.text()
                try:
                    val_t_stripped = val_t.strip()
                    if(val_t_stripped):
                        if val_t_stripped[0] == "=":
                            val = val_t_stripped[1:]
                            data_item.setText("%s" % val)
                        else:
                            val = eval(val_t_stripped)
                    else:
                        val = eval(val_t_stripped)
                    self.data_items[(rown,coln)] = data_item
                    self.context[self.row_titles[rown]]= val
                except:
                    self.data_items[(rown,coln)] = data_item
                    data_item.setText("%s" % self.context[self.row_titles[rown]])


    def eval(self, trigger=None, guard=None):
        SCRUB_LIST = collections.OrderedDict([
        ])

        if trigger.strip() == guard.strip() == "":
            return True
        else:
            t = g = False
            if trigger.strip():
                trigger_cleaned = trigger.strip().replace("\n", " ")
                for k in SCRUB_LIST:
                    trigger_cleaned = trigger_cleaned.replace(k,SCRUB_LIST[k])
                t = eval(trigger_cleaned.replace("\n", " "), self.context)
            if guard.strip():
                guard_cleaned = guard.strip().replace("\n", " ")
                for k in SCRUB_LIST:
                    guard_cleaned = guard_cleaned.replace(k,SCRUB_LIST[k])
                g = eval(guard_cleaned, self.context)
            return (t or g)


class TrafficLight(QWidget):
    """
    This object is the overall container of both the context table and the
    state chart representation.
    """
    def __init__(self, parent=None):
        super(TrafficLight, self).__init__(parent)
        self.layout = QHBoxLayout()

    def add(self, sc, sc_context):
        spLeft = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        spLeft.setHorizontalStretch(1)
        spRight = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        spRight.setHorizontalStretch(3)

        sc_context.setSizePolicy(spLeft)
        sc.setSizePolicy(spRight)

        self.layout.addWidget(sc_context, 0)
        self.layout.addWidget(sc, 0)

        self.setLayout(self.layout)
        self.setWindowTitle("Traffic Light State")
        self.resize(1200, 900)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    sc_file = os.path.join(THIS_SCRIPT_LOCATION, 'traffic_light_state.svg')
    sc1 = scsvg.StateChart(sc_file)
    sc1.refresh(True)
    sc1_context = TrafficLight_SC()
    sc1.configure(sc1_context, [])

    sc1_all = TrafficLight()
    sc1_all.add(sc1, sc1_context)
    sc1_all.show()

    sys.exit(app.exec_())

