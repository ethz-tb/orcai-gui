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


class TextItem(TextItem):
    """Extend TextItem with setOpts function to unify interface with BarGraphItem."""

    def setOpts(self, **opts):
        """Set options for the TextItem."""
        if "text_color" in opts:
            self.setColor(opts["text_color"])


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
        self.hideButtons()


class SpectrogramWidget(GraphicsLayoutWidget):
    """A custom plot widget showing the spectrogram and predictions."""

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
                pen=mkPen(
                    self._get_call_color(call),
                ),
                name=self.calls[i],
            )
            self.prediction_legend.addItem(self.prediction_plot.items[-1], call)

        for label in self.data.predicted_labels.itertuples():
            prediction_bgitem = BarGraphItem(
                x0=label.start,
                x1=label.stop,
                y0=0.25,
                y1=0.75,
                brush=mkBrush(
                    self._get_call_color(label.label, alpha=0.3),
                ),
                pen=mkPen(self._get_call_color(label.label, alpha=0.7)),
            )
            prediction_bgitem.setObjectName(str(label.Index))
            # Can't use same item (and .copy() doesn't work)
            navigation_bgitem = BarGraphItem(
                x0=label.start,
                x1=label.stop,
                y0=0.25,
                y1=0.75,
                brush=mkBrush(
                    self._get_call_color(label.label, alpha=0.3),
                ),
                pen=mkPen(self._get_call_color(label.label, alpha=0.7)),
            )
            navigation_bgitem.setObjectName(str(label.Index))

            call_label = TextItem(
                text=label.label,
                color=self._get_call_color(label.label, alpha=0.7),
                anchor=(0.5, 0.5),
            )
            call_label.setObjectName(str(label.Index))
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

    def update_prediction_label(self, label_ok: bool, label_index: int):
        print(self.data.predicted_labels.to_numpy())
        label = self.data.predicted_labels.iloc[label_index]
        prediction_plot_items = [
            x for x in self.prediction_plot.items if x.objectName() == str(label_index)
        ]
        navigation_plot_items = [
            x for x in self.navigation_plot.items if x.objectName() == str(label_index)
        ]
        if label_ok:
            prediction_plot_brush = mkBrush(
                self._get_call_color(label.label, alpha=0.3)
            )
            prediction_plot_pen = mkPen((0, 255, 0, 200), width=2)
            prediction_plot_text_color = self._get_call_color(label.label, alpha=0.7)
            navigation_plot_brush = prediction_plot_brush
            navigation_plot_pen = mkPen(self._get_call_color(label.label, alpha=0.7))
        else:
            prediction_plot_brush = (100, 100, 100, int(0.5 * 255))
            prediction_plot_pen = (200, 200, 200, int(0.5 * 255))
            prediction_plot_text_color = prediction_plot_pen
            navigation_plot_brush = prediction_plot_brush
            navigation_plot_pen = prediction_plot_pen

        for item in prediction_plot_items:
            item.setOpts(
                brush=prediction_plot_brush,
                pen=prediction_plot_pen,
                text_color=prediction_plot_text_color,
            )
        for item in navigation_plot_items:
            item.setOpts(
                brush=navigation_plot_brush,
                pen=navigation_plot_pen,
            )

    def update_plot_region(self, region):
        region = self.navigation_region.getRegion()
        self.spectrogram_plot.setRange(xRange=region, disableAutoRange=True)
        self.prediction_plot.setRange(xRange=region, disableAutoRange=True)

    def set_colormap(self, colormap_name):
        """Set the colormap for the spectrogram."""
        if colormap_name == self.colormap_name:
            return
        if self.spectrogram is None:
            return
        self.colormap_name = colormap_name
        lut = colormap.get(self.colormap_name, source="matplotlib").getLookupTable()

        self.spectrogram_image.setLookupTable(lut)

    def focus_on_label(self, label_index):
        """Focus on a specific label in the spectrogram."""

        label = self.data.predicted_labels.iloc[label_index]
        start, stop = label.start, label.stop
        duration = stop - start
        extra = (
            (self.max_label_duration * (1 + self.expand_focus_region)) - duration
        ) / 2

        self.navigation_region.setRegion([start - extra, stop + extra])

    def _get_call_color(self, call: str, alpha: float = 1):
        call = call.replace("*", "")
        i = self.calls.index(call)
        if alpha < 0:
            alpha = 0
        if alpha > 1:
            alpha = 255
        else:
            alpha = 255 * alpha

        return intColor(i, alpha=int(alpha), hues=len(self.calls))
