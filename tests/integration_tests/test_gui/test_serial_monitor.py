from soniccontrol_gui.utils.testing import widget_names
from soniccontrol_gui.utils.testing.gui_controller import GuiController
import pytest

@pytest.mark.asyncio
async def test_set_gain_over_serial_updates_status_bar():
    controller = GuiController()
    controller.switch_to_tab(widget_names.SERIAL_MONITOR_TAB)
    controller.set_widget_text(widget_names.SERIAL_MONITOR_COMMAND_LINE_INPUT_ENTRY, "!gain=50")
    controller.press_button(widget_names.SERIAL_MONITOR_SEND_BUTTON)
    text = await controller.wait_for_widget_to_change_text(widget_names.STATUS_BAR_GAIN_LABEL, 1.0)
    assert "50 %" in text, f"Expected the gain to be 50 %, but the label is set to {text}"

