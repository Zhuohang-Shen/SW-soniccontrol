import asyncio
from soniccontrol_gui.utils.testing import widget_names
from soniccontrol_gui.utils.testing.gui_controller import GuiController
import pytest

@pytest.mark.asyncio(loop_scope="package")
async def test_set_gain_over_serial_updates_status_bar():
    controller = GuiController()
    controller.switch_to_tab(widget_names.SERIAL_MONITOR_TAB)
    controller.set_widget_text(widget_names.SERIAL_MONITOR_COMMAND_LINE_INPUT_ENTRY, "!gain=50")
    controller.press_button(widget_names.SERIAL_MONITOR_SEND_BUTTON)
    text = await controller.wait_for_widget_to_change_text(widget_names.STATUS_BAR_GAIN_LABEL, 1.0)
    assert "50 %" in text, f"Expected the gain to be 50 %, but the label is set to {text}"


@pytest.mark.asyncio(loop_scope="package")
async def test_sending_a_command_displays_it_in_the_monitor(connection_window):
    controller = GuiController()
    command = "?info"
    controller.switch_to_tab(widget_names.SERIAL_MONITOR_TAB)
    controller.set_widget_text(widget_names.SERIAL_MONITOR_COMMAND_LINE_INPUT_ENTRY, command)
    controller.press_button(widget_names.SERIAL_MONITOR_SEND_BUTTON)
    await controller.execute_events_until_idle()
    command_entry = controller.get_text_of_widget_child(widget_names.SERIAL_MONITOR_SCROLL_FRAME, -1)
    assert command in command_entry, f"The command '{command}' is not part of the serial monitor output '{command_entry}'"

