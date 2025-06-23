import pandas as pd
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from pyqtgraph import (
    AxisItem,
    BarGraphItem,
    GraphicsLayoutWidget,
    ImageItem,
    LegendItem,
    LinearRegionItem,
    PlotItem,
    TextItem,
    colormap,
    intColor,
    mkBrush,
    mkPen,
)

from orcaigui.extensions import timedelta
from orcaigui.orcaidata import OrcaiData

CORRECT_PEN_COLOR = (0, 255, 0, int(0.7 * 255))
WRONG_PEN_COLOR = (200, 200, 200, int(0.5 * 255))
WRONG_BRUSH_COLOR = (100, 100, 100, int(0.5 * 255))


def _get_call_color(call: str, calls: list[str], alpha: float = 1):
    call = call.replace("*", "")
    i = calls.index(call)
    if alpha < 0:
        alpha = 0
    if alpha > 1:
        alpha = 255
    else:
        alpha = 255 * alpha

    return intColor(i, alpha=int(alpha), hues=len(calls))


class LabelTextItem(TextItem):
    def __init__(self, label, calls):
        self.calls = calls
        if not label.label_checked:
            color = _get_call_color(label.label, self.calls, alpha=0.7)
        else:
            if label.label_ok:
                color = _get_call_color(label.label, self.calls, alpha=0.7)
            else:
                color = WRONG_PEN_COLOR
        super().__init__(
            text=label.label,
            color=color,
            anchor=(0.5, 0.5),
        )
        self.setObjectName(str(label.Index))

    def update_item(self, label, update_extent: bool = False):
        if not label.label_checked:
            self.setColor(_get_call_color(label.label, self.calls, alpha=0.7))
        else:
            if label.label_ok:
                self.setColor(_get_call_color(label.label, self.calls, alpha=0.7))
            else:
                self.setColor(WRONG_PEN_COLOR)
        if update_extent:
            self.setPos((label.start + label.stop) / 2, 0.5)


class LabelItem(BarGraphItem):
    def __init__(self, label, calls):
        self.calls = calls
        if not label.label_checked:
            brush = mkBrush(
                _get_call_color(label.label, calls=self.calls, alpha=0.3),
            )
            pen = mkPen(_get_call_color(label.label, calls=self.calls, alpha=0.7))
        else:
            if label.label_ok:
                brush = mkBrush(
                    _get_call_color(label.label, calls=self.calls, alpha=0.3),
                )
                pen = mkPen(CORRECT_PEN_COLOR, width=2)
            else:
                brush = mkBrush(WRONG_BRUSH_COLOR)
                pen = mkPen(WRONG_PEN_COLOR)
        super().__init__(
            x0=label.start, x1=label.stop, y0=0.25, y1=0.75, brush=brush, pen=pen
        )
        self.setObjectName(str(label.Index))

    def update_item(self, label, update_extent: bool = False):
        if not label.label_checked:
            self.setOpts(
                brush=mkBrush(
                    _get_call_color(label.label, self.calls, alpha=0.3),
                ),
                pen=mkPen(_get_call_color(label.label, self.calls, alpha=0.7)),
            )
        else:
            if label.label_ok:
                self.setOpts(
                    brush=mkBrush(
                        _get_call_color(label.label, self.calls, alpha=0.3),
                    ),
                    pen=mkPen(CORRECT_PEN_COLOR, width=2),
                )
            else:
                self.setOpts(
                    brush=mkBrush(WRONG_BRUSH_COLOR),
                    pen=mkPen(WRONG_PEN_COLOR),
                )
        if update_extent:
            self.setOpts(x0=label.start, x1=label.stop)


class DurationAxisItem(AxisItem):
    def __init__(self, scale: float):
        super().__init__(orientation="bottom")
        self.setScale(scale)

    def tickStrings(self, values, scale, spacing):
        """Format tick labels as HH:MM:SS or HH:MM:SS.sss."""

        low_range = spacing * scale < 1
        return [
            timedelta(seconds=v * scale).to_string(ms_f="03.0f" if low_range else None)
            for v in values
        ]


class YAxisItem(AxisItem):
    def __init__(
        self,
        label: str,
        units: str | None,
        range: tuple,
        scale: float = 1.0,
        ticks: list = None,
    ):
        super().__init__(orientation="left")
        self.setStyle(
            tickTextWidth=15,
            autoExpandTextSpace=False,
            autoReduceTextSpace=False,
        )
        self.setLabel(label, units=units)
        self.setRange(*range)
        self.setScale(scale)
        if ticks is not None:
            self.setTicks(ticks)


class TimePlot(PlotItem):
    def __init__(
        self,
        x_scale: float,
        y_label: str,
        y_units: str,
        y_range: list,
        y_scale: float = 1.0,
        y_ticks: list | None = None,
        hide_y_axis: bool = False,
        max_height: int | None = None,
    ):
        axisItems = {
            "bottom": DurationAxisItem(scale=x_scale),
            "left": YAxisItem(
                label=y_label,
                units=y_units,
                range=y_range,
                scale=y_scale,
                ticks=y_ticks,
            ),
        }
        super().__init__(axisItems=axisItems)
        self.setMouseEnabled(x=False, y=False)
        self.setLimits(xMin=0)
        self.hideButtons()
        self.setMenuEnabled(False)
        if hide_y_axis:
            self.hideAxis("bottom")
        if max_height is not None:
            self.setMaximumHeight(max_height)


class NavigationPlot(PlotItem):
    def __init__(
        self,
        x_scale: float,
        max_height: int = 25,
        background_color=(50, 50, 50),
        enableMenu=False,
    ):
        axisItems = {"bottom": DurationAxisItem(scale=x_scale)}
        super().__init__(axisItems=axisItems, enableMenu=enableMenu)
        self.hideAxis("left")
        self.hideAxis("bottom")
        self.setMaximumHeight(max_height)
        self.setMouseEnabled(x=False, y=False)
        self.getViewBox().setBackgroundColor(background_color)
        self.setMenuEnabled(False)
        self.hideButtons()


class SpectrogramWidget(GraphicsLayoutWidget):
    """A custom plot widget showing the spectrogram and predictions."""

    clicked_label = pyqtSignal(int)
    new_label = pyqtSignal(int)

    def __init__(
        self,
        spectrogram_parameter: dict,
        calls: list[str],
        max_x_range=1500,
        colormap_name="Greys",
        expand_focus_region=0.1,  # expand the focus region by 10% -> length(longest label) * (1 + expand_focus_region)
        parent=None,
    ):
        super().__init__(parent)

        self.data = None
        self.calls = calls
        self.max_x_range = max_x_range
        self.colormap_name = colormap_name
        self.expand_focus_region = expand_focus_region

        x_scale = (
            spectrogram_parameter["n_overlap"] / spectrogram_parameter["sampling_rate"]
        )

        self.spectrogram_plot = TimePlot(
            x_scale=x_scale,
            y_label="Frequency",
            y_units="Hz",
            y_range=(0, spectrogram_parameter["n_overlap"] + 1),
            y_scale=(spectrogram_parameter["sampling_rate"] / 2)
            / spectrogram_parameter["n_overlap"],
            hide_y_axis=True,
        )

        self.prediction_plot = TimePlot(
            x_scale=x_scale,
            y_label="Probability",
            y_units=None,
            y_range=[-0.3, 1.0],
            y_ticks=[
                [
                    (0.0, "0"),
                    (0.5, "0.5"),
                    (1.0, "1"),
                ],
                [],
            ],
            max_height=100,
        )
        self.prediction_plot.setXLink(self.spectrogram_plot)

        self.navigation_plot = NavigationPlot(
            x_scale=x_scale,
            max_height=25,
            background_color=(50, 50, 50),
        )

        self.addItem(self.spectrogram_plot, row=0, col=0)

        self.addItem(self.prediction_plot, row=1, col=0)
        self.prediction_legend_box = self.addViewBox(
            row=2, col=0, enableMouse=False, lockAspect=False
        )
        self.prediction_legend = LegendItem(colCount=len(self.calls))
        self.prediction_legend.setParentItem(self.prediction_legend_box)
        self.prediction_legend.anchor((0.5, 0.5), (0.5, 0.5))
        self.prediction_legend.mouseDragEvent = lambda *args, **kwargs: None
        self.prediction_legend.hoverEvent = lambda *args, **kwargs: None
        self.prediction_legend_box.setMaximumHeight(10)

        self.addItem(self.navigation_plot, row=3, col=0)

    def update_data(
        self,
        data: OrcaiData,
        colormap_name: str = "Greys",
    ):
        """Update the plot data with new spectrogram and predictions."""
        self.data = data
        self.max_label_duration = (
            max(
                self.data.predicted_labels["stop"] - self.data.predicted_labels["start"]
            )
            if not self.data.predicted_labels.empty
            else 0
        )
        self.plot_x_max = len(self.data.times) * 1.05
        self.plot_x_range = [
            0,
            self.plot_x_max
            if len(self.data.times) <= self.max_x_range
            else self.max_x_range,
        ]
        self.colormap_name = colormap_name
        self.update_plots()

    def update_plots(self):
        """Update the spectrogram plot"""
        if self.data is None:
            self.status.showMessage("No data available")
            return

        self.spectrogram_image = ImageItem()
        self.spectrogram_image.setImage(self.data.spectrogram.T)
        lut = colormap.get(self.colormap_name, source="matplotlib").getLookupTable()
        self.spectrogram_image.setLookupTable(lut)

        self.spectrogram_plot.clear()
        self.spectrogram_plot.addItem(self.spectrogram_image)

        self.spectrogram_plot.setLimits(xMin=0, xMax=self.plot_x_max)
        self.spectrogram_plot.setRange(xRange=self.plot_x_range)

        self.prediction_plot.clear()
        self.navigation_plot.clear()
        self.prediction_legend.clear()

        self.navigation_plot.setLimits(xMin=0, xMax=self.plot_x_max)
        self.navigation_plot.setRange(xRange=[0, self.plot_x_max])
        self.navigation_region = LinearRegionItem(
            values=self.plot_x_range,
            bounds=[0, self.plot_x_max],
            brush=mkBrush(255, 255, 255, 50),
            movable=True,
        )
        self.navigation_region.sigRegionChangeFinished.connect(self.update_plot_region)
        self.navigation_plot.addItem(
            self.navigation_region,
        )

        for i, call in enumerate(self.calls):
            self.prediction_plot.plot(
                x=self.data.prediction_times,
                y=self.data.aggregated_predictions[:, i],
                pen=mkPen(_get_call_color(call, self.calls)),
                name=self.calls[i],
            )
            self.prediction_legend.addItem(self.prediction_plot.items[-1], call)

        for label in self.data.predicted_labels.itertuples():
            prediction_bgitem = LabelItem(label, calls=self.calls)
            # Can't use same item (and .copy() doesn't work)
            navigation_bgitem = LabelItem(label, calls=self.calls)

            call_label = LabelTextItem(label, calls=self.calls)
            self.prediction_plot.addItem(prediction_bgitem)
            self.navigation_plot.addItem(navigation_bgitem)
            self.prediction_plot.addItem(call_label)
            call_label.setPos(
                (label.start + label.stop) / 2,
                0.5,
            )
        self.prediction_plot.setLimits(xMin=0, xMax=self.plot_x_max)
        self.prediction_plot.setRange(xRange=self.plot_x_range)
        self.prediction_plot.showGrid(x=True, y=True)
        self.prediction_plot.scene().sigMouseClicked.connect(
            self.mouse_clicked_prediction_plot
        )

    def mouse_clicked_prediction_plot(self, ev):
        if not ev.double():
            return
        if self.data is None:
            return

        pos = self.prediction_plot.vb.mapSceneToView(ev.scenePos())
        print(f"double-clicked at {pos.x()}, {pos.y()}")
        if pos.x() < 0 or pos.x() > self.plot_x_max:
            return
        if pos.y() < 0 or pos.y() > 1:
            return

        # Check if a label was clicked
        near_bg_items = [
            x
            for x in self.prediction_plot.scene().itemsNearEvent(ev)
            if isinstance(x, BarGraphItem)
        ]
        if len(near_bg_items) > 0:
            label_index = int(near_bg_items[0].objectName())
            self.clicked_label.emit(label_index)
            return
        else:
            start = int(pos.x())
            self.new_label.emit(start)

    @pyqtSlot(int, bool)
    def update_prediction_label(
        self,
        label_index: int,
        update_extent: bool = False,
    ):
        label = self.data.predicted_labels.iloc[label_index]

        prediction_plot_items = [
            x for x in self.prediction_plot.items if x.objectName() == str(label_index)
        ]
        navigation_plot_items = [
            x for x in self.navigation_plot.items if x.objectName() == str(label_index)
        ]

        for item in prediction_plot_items:
            item.update_item(label, update_extent=update_extent)

        for item in navigation_plot_items:
            item.update_item(label, update_extent=update_extent)

    def update_plot_region(self, region):
        region = self.navigation_region.getRegion()
        self.spectrogram_plot.setRange(xRange=region, disableAutoRange=True)
        self.prediction_plot.setRange(xRange=region, disableAutoRange=True)

    def set_colormap(self, colormap_name):
        """Set the colormap for the spectrogram."""
        if colormap_name == self.colormap_name:
            return
        if self.data.spectrogram is None:
            return
        self.colormap_name = colormap_name
        lut = colormap.get(self.colormap_name, source="matplotlib").getLookupTable()

        self.spectrogram_image.setLookupTable(lut)

    @pyqtSlot(int)
    def focus_on_label(self, label_index):
        """Focus on a specific label in the spectrogram."""

        label = self.data.predicted_labels.iloc[label_index]
        start, stop = label.start, label.stop
        duration = stop - start
        extra = (
            (self.max_label_duration * (1 + self.expand_focus_region)) - duration
        ) / 2

        self.navigation_region.setRegion([start - extra, stop + extra])

        # add roi region to spectrogram plot
        if hasattr(self, "label_adjust_region"):
            self.spectrogram_plot.removeItem(self.label_adjust_region)
        self.label_adjust_region = LinearRegionItem(
            values=[start, stop],
            bounds=[0, self.plot_x_max],
            brush=mkBrush(255, 255, 255, 50),
            movable=True,
        )
        self.label_adjust_region.sigRegionChangeFinished.connect(self.adjust_label)
        self.current_label = label_index
        self.spectrogram_plot.addItem(self.label_adjust_region)

    @pyqtSlot()
    def adjust_label(self):
        region = self.label_adjust_region.getRegion()
        self.data.predicted_labels.loc[self.current_label, "start"] = int(region[0])
        self.data.predicted_labels.loc[self.current_label, "stop"] = int(region[1])
        self.update_prediction_label(self.current_label, update_extent=True)
        return
