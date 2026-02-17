import asyncio
from pathlib import Path
from async_tkinter_loop import main_loop
import pytest
import pytest_asyncio
from ttkbootstrap.utility import enable_high_dpi_awareness
import tkinter as tk
import ttkbootstrap as ttk

from soniccontrol.app_config import PLATFORM, System
from soniccontrol_gui.plugins.device_plugin import register_device_plugins
from soniccontrol_gui.utils.image_loader import ImageLoader
from soniccontrol_gui.utils.widget_registry import WidgetRegistry, get_text_of_widget, set_text_of_widget
from soniccontrol_gui.view import TabView
from soniccontrol_gui.views.core.connection_window import ConnectionWindow
from soniccontrol_gui.widgets.notebook import Notebook
from tests.integration_tests.conftest import Profile
from soniccontrol_gui import widget_names


class GuiController:
    def is_widget_registered(self, widget_name: str) -> bool:
        return WidgetRegistry.is_widget_registered(widget_name)
    
    async def wait_for_widget_to_be_registered(self, widget_name: str):
        await WidgetRegistry.wait_for_widget_to_be_registered(widget_name)

    async def wait_for_widget_to_change_text(self, widget_name: str):
        return await WidgetRegistry.wait_for_widget_to_change_text(widget_name)
    
    def get_widget_text(self, widget_name: str) -> str:
        widget = WidgetRegistry.get_widget(widget_name)
        return get_text_of_widget(widget)
    
    def set_widget_text(self, widget_name: str, text: str) -> None:
        widget = WidgetRegistry.get_widget(widget_name)
        set_text_of_widget(widget, text)

    def press_button(self, widget_name: str):
        widget = WidgetRegistry.get_widget(widget_name)
        if isinstance(widget, (tk.Button, ttk.Button, ttk.Checkbutton)):
            widget.invoke()
        else:
            raise TypeError(f"The registered object '{widget_name}' is not a button")

    def switch_to_tab(self, widget_name: str) -> None:
        tab_view = WidgetRegistry.get_widget(widget_name)
        if not isinstance(tab_view, TabView):
            raise TypeError(f"The registered object '{widget_name}' is not a tab view")

        parent_name = widget_name.split(".")[0]
        notebook = WidgetRegistry.get_widget(parent_name)
        if not isinstance(notebook, (Notebook, ttk.Notebook)):
            raise TypeError(f"The registered object '{parent_name}' is not a notebook")
        notebook.select(tab_view)

    def get_text_of_widget_child(self, widget_name: str, index_child: int) -> str:   
        """
            @brief gets the text of the ith child of the widget.
            @usage Useful for inspecting the monitor tab.
        """      
        widget = WidgetRegistry.get_widget(widget_name)
        assert isinstance(widget, tk.Widget), "widget has to be an instance or subclass of tk.Widget"
        child = widget.winfo_children()[index_child]
        return get_text_of_widget(child)     



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


@pytest_asyncio.fixture(scope="module")
async def device_window(request, connection_window):
    controller = GuiController()    

    profile: Profile = request.config._sonic_control_plugin.profile
    url: str = request.config._sonic_control_plugin.url

    if profile == Profile.device_descale or profile == Profile.device_worker:
        controller.set_widget_text(widget_names.CONNECTION_PORTS_COMBOBOX, url)
        # calling this method directly here ensures 
        # that the whole device window gets loaded, 
        # before continuing 
        await connection_window._on_connect_via_url() 
    else:
        if profile == Profile.simulation_descale:
            controller.set_widget_text(widget_names.CONNECTION_SIMULATION_CMD_ARGS, "--name=test_descale --profile=descale")
        elif profile == Profile.simulation_worker:
            controller.set_widget_text(widget_names.CONNECTION_SIMULATION_CMD_ARGS, "--name=test_worker --profile=worker")
        else:
            raise NotImplementedError(f"For the {profile} no case is implemented")

        # calling this method directly here ensures 
        # that the whole device window gets loaded, 
        # before continuing 
        await connection_window._on_connect_via_simulation()
