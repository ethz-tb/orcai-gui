from orcAI.auxiliary import seconds_to_hms
from pyqtgraph import AxisItem


class hhmmssAxisItem(AxisItem):
    def tickStrings(self, values, scale, spacing):
        """Format tick labels as HH:MM:SS"""
        return [seconds_to_hms(v * scale) for v in values]
