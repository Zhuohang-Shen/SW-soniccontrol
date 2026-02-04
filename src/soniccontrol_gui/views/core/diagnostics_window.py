import logging
from typing import List
from soniccontrol.hw_tests.test_base import TestInfo
from soniccontrol.hw_tests.test_executor import TestExecutor
from soniccontrol_gui.ui_component import UIComponent
from soniccontrol_gui.utils.image_loader import ImageLoader
from soniccontrol_gui.view import TabView
from soniccontrol_gui.views.core.device_window import DeviceWindow
import ttkbootstrap as ttk
from soniccontrol_gui.constants import ui_labels, sizes
from soniccontrol_gui.resources import images
from soniccontrol_gui.widgets.test_widget import TestWidget



class HwTestingTab(UIComponent):
    def __init__(self, parent: UIComponent, test_executor: TestExecutor):
        self._logger = logging.getLogger(parent.logger.name + "." + HwTestingTab.__name__)

        self._test_executor = test_executor

        self._view = HwTestingTabView(parent.view)
        self._tests: List[TestInfo] = []
        super().__init__(parent, self._view, self._logger)

    async def _discover_tests(self):
        self._tests = await self._test_executor.load_tests()


class DiagnosticsWindow(DeviceWindow):
    pass



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
