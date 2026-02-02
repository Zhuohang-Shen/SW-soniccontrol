import logging
from typing import Callable
from soniccontrol.events import PropertyChangeEvent
from soniccontrol.hw_tests.test_base import TestInfo
from soniccontrol_gui.ui_component import UIComponent
from soniccontrol_gui.utils.image_loader import ImageLoader
from soniccontrol_gui.view import TabView, View
from soniccontrol_gui.views.core.device_window import DeviceWindow
import ttkbootstrap as ttk
from soniccontrol_gui.constants import ui_labels, sizes
from soniccontrol_gui.resources import images


class TestWidget(UIComponent):
    def __init__(self, parent: UIComponent, parent_slot: View, test_info: TestInfo):
        self._logger = logging.getLogger(parent.logger.name + "." + HwTestingTab.__name__)
        self._test_info = test_info

        self._view = TestWidgetView(parent_slot, self._test_info.suite_name, self._test_info.test_name)
        super().__init__(parent, self._view, self._logger)

    def on_test_is_running_changed(self, _: PropertyChangeEvent):
        pass


class HwTestingTab(UIComponent):
    def __init__(self, parent: UIComponent):
        self._logger = logging.getLogger(parent.logger.name + "." + HwTestingTab.__name__)

        self._view = HwTestingTabView(parent.view)
        super().__init__(parent, self._view, self._logger)


class DiagnosticsWindow(DeviceWindow):
    pass


class TestWidgetView(View):
    def __init__(self, master: ttk.Frame, suite_name: str, test_name: str, *args, **kwargs) -> None:
        self._suite_name = suite_name
        self._test_name = test_name
        super().__init__(master, *args, **kwargs)

    def _initialize_children(self) -> None:
        self._suite_label = ttk.Label(self, text=self._suite_name)
        self._test_label = ttk.Label(self, text=self._test_name)
        
        self._test_result_text_var = ttk.StringVar(self, value="")
        self._test_result_label = ttk.Label(self, textvariable=self._test_result_text_var)

        self._run_test_button = ttk.Button(self, text=ui_labels.RUN_LABEL)
        self._stop_test_button = ttk.Button(self, text=ui_labels.STOP_LABEL)

    def _initialize_publish(self) -> None:
        self.pack(fill=ttk.X, side=ttk.TOP, pady=sizes.MEDIUM_PADDING)

        self._suite_label.pack(side=ttk.LEFT, padx=sizes.SMALL_PADDING)
        self._test_label.pack(side=ttk.LEFT, padx=sizes.SMALL_PADDING, expand=True)
        self._run_test_button.pack(side=ttk.RIGHT, padx=sizes.SMALL_PADDING)
        self._test_result_label.pack(side=ttk.RIGHT, padx=sizes.SMALL_PADDING)

    @property
    def test_result(self) -> str:
        return self._test_result_text_var.get()
    
    @test_result.setter
    def test_result(self, value: str):
        self._test_result_text_var.set(value)

    def set_run_test_button_callback(self, callback: Callable[[], None]):
        self._run_test_button.configure(command=callback)

    def set_stop_test_button_callback(self, callback: Callable[[], None]):
        self._stop_test_button.configure(command=callback)

    def set_run_test_button_enabled(self, enabled: bool) -> None:
        self._run_test_button.configure(state=ttk.NORMAL if enabled else ttk.DISABLED)

    def set_stop_test_button_enabled(self, enabled: bool) -> None:
        self._stop_test_button.configure(state=ttk.NORMAL if enabled else ttk.DISABLED)


class HwTestingTabView(TabView):
    def __init__(self, master: ttk.Frame, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)

    @property
    def image(self) -> ttk.ImageTk.PhotoImage:
        return ImageLoader.load_image_resource(images.HOME_ICON_BLACK, sizes.TAB_ICON_SIZE)

    @property
    def tab_title(self) -> str:
        return ui_labels.HOME_LABEL

    def _initialize_children(self) -> None:
        pass

    def _initialize_publish(self) -> None:
        pass
