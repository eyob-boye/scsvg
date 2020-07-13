import sys
import os
import random
from PySide2 import QtCore
from PySide2.QtWidgets import QApplication

# Some pathes needed for locating import from relative path.
THIS_SCRIPT_LOCATION = os.path.dirname(__file__)
SCSVG_LOCATION = os.path.join(THIS_SCRIPT_LOCATION, "../..")
sys.path.append(SCSVG_LOCATION)

import scsvg


if __name__ == '__main__':
    app = QApplication(sys.argv)

    sc_file = os.path.join(THIS_SCRIPT_LOCATION, 'traffic_light_state.svg')
    sc1 = scsvg.StateChart(sc_file)
    sc1.refresh(True)
    sc1.configure(None, [])
    sc1.show()

    sys.exit(app.exec_())

