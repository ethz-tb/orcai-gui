import rich_click as click

from orcaigui.main import predict_gui

click.rich_click.STYLE_OPTIONS_PANEL_BOX = "SIMPLE"
click.rich_click.STYLE_COMMANDS_PANEL_BOX = "SIMPLE"
click.rich_click.STYLE_COMMANDS_PANEL_BORDER = "bold"
click.rich_click.STYLE_OPTIONS_PANEL_BORDER = "bold"
click.rich_click.MAX_WIDTH = 100


@click.command()
def cli():
    predict_gui()
