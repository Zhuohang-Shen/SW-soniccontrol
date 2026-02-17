import asyncio
from pathlib import Path
from async_tkinter_loop import main_loop
import pytest
import pytest_asyncio
from ttkbootstrap.utility import enable_high_dpi_awareness

from soniccontrol.app_config import PLATFORM, System
from soniccontrol_gui.plugins.device_plugin import register_device_plugins
from soniccontrol_gui.utils.image_loader import ImageLoader
from soniccontrol_gui.utils.widget_registry import WidgetRegistry
from soniccontrol_gui.views.core.connection_window import ConnectionWindow
from tests.integration_tests.conftest import Profile
from soniccontrol_gui.utils.testing import widget_names
from soniccontrol_gui.utils.testing.gui_controller import GuiController


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def connection_window(request, event_loop):
    simulation_exe_path: Path = request.config._sonic_control_plugin.simulation_exe_path

    ImageLoader.clear_resources()
    WidgetRegistry.set_up(event_loop)
    register_device_plugins()

    connection_window = ConnectionWindow(simulation_exe_path)
    
    if PLATFORM != System.WINDOWS:
        enable_high_dpi_awareness(connection_window.view)
    root = connection_window.view.winfo_toplevel()
    event_loop.create_task(main_loop(connection_window.view)) # type: ignore

    yield connection_window

    root.destroy()
    event_loop.run_until_complete(WidgetRegistry.clean_up())
    ImageLoader.clear_resources()


@pytest_asyncio.fixture(scope="module", autouse=True)
async def device_window(request, connection_window, tmp_path):
    controller = GuiController()    

    profile: Profile = request.config._sonic_control_plugin.profile
    url: str = request.config._sonic_control_plugin.url

    if profile == Profile.device_descale or profile == Profile.device_worker:
        controller.set_widget_text(widget_names.CONNECTION_PORTS_COMBOBOX, url)
        # calling this method directly here ensures 
        # that the whole device window gets loaded, 
        # before continuing 
        connection_window._on_connect_via_url() 
    else:
        if profile == Profile.simulation_descale:
            controller.set_widget_text(
                widget_names.CONNECTION_SIMULATION_CMD_ARGS, 
                f"--name=test_descale --profile=descale --data-dir=\"{tmp_path}\""
            )
        elif profile == Profile.simulation_worker:
            controller.set_widget_text(
                widget_names.CONNECTION_SIMULATION_CMD_ARGS, 
                f"--name=test_worker --profile=worker --data-dir=\"{tmp_path}\""
            )
        else:
            raise NotImplementedError(f"For the {profile} no case is implemented")

        # calling this method directly here ensures 
        # that the whole device window gets loaded, 
        # before continuing 
        connection_window._on_connect_to_simulation()
    await connection_window.wait_until_connected()
    connection_window._view.update() # handle all events from tkinter. Ensure everything is loaded
