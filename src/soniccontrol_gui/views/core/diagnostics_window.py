import logging
from typing import List
import asyncio
from async_tkinter_loop import async_handler
from ttkbootstrap.scrolled import ScrolledFrame
from soniccontrol.hw_tests.test_base import TestInteraction, TestResult
from soniccontrol.events import Event, PropertyChangeEvent
from soniccontrol.hw_tests.test_base import SemiAutomatedStep, TestInfo
from soniccontrol.hw_tests.test_executor import TestExecutor
from soniccontrol.sonic_device import SonicDevice
from soniccontrol_gui.ui_component import UIComponent
from soniccontrol_gui.utils.image_loader import ImageLoader
from soniccontrol_gui.view import TabView, View
from soniccontrol_gui.views.control.logging import Logging
from soniccontrol_gui.views.control.serialmonitor import SerialMonitor
from soniccontrol_gui.views.core.app_state import AppState, ExecutionState
from soniccontrol_gui.views.core.device_window import DeviceWindow, DeviceWindowView
import ttkbootstrap as ttk
from soniccontrol_gui.constants import ui_labels, sizes
from soniccontrol_gui.resources import images
from soniccontrol_gui.widgets.message_box import DialogOptions, MessageBox
from soniccontrol_gui.widgets.test_widget import TestWidget



class HwTestingTab(UIComponent):
    def __init__(self, parent: UIComponent, test_executor: TestExecutor):
        self._logger = logging.getLogger(parent.logger.name + "." + HwTestingTab.__name__)

        self._test_executor = test_executor

        self._view = HwTestingTabView(parent.view)
        self._test_discovery_task = asyncio.create_task(self._discover_tests())
        self._test_widgets: List[TestWidget] = []
        super().__init__(parent, self._view, self._logger)

        self._test_executor.subscribe(TestExecutor.NEEDS_USER_INTERACTION_EVENT, self._on_user_interaction_needed)

    async def _discover_tests(self):
        tests = await self._test_executor.load_tests()
        for test_info in tests:
            test_widget = TestWidget(self, self._view.tests_frame, test_info)

            test_widget.subscribe(TestWidget.RUN_TEST_EVENT, self._on_run_test_with_index)
            test_widget.subscribe(TestWidget.STOP_TEST_EVENT, self._stop_test)
            self._test_executor.subscribe_property_listener(TestExecutor.RUNNING_TEST_INDEX_PROPERTY, test_widget.on_running_test_index_changed)

            self._test_widgets.append(test_widget)
        self._view.update_idletasks() # is needed to update the scroll view, so that it shows the widgets inside

    def _on_run_test_with_index(self, e: Event):
        test = e.data["test"]
        self._test_executor.run_test(test)

    @async_handler
    async def _stop_test(self, _):
        await self._test_executor.stop_test()

    @async_handler
    async def _on_user_interaction_needed(self, event: Event):
        semi_automated_step: SemiAutomatedStep = event.data["semi_automated_step"]
        test: TestInfo = event.data["test"]

        if semi_automated_step.interaction == TestInteraction.PHYSICAL_INTERACTION:
            msg_box = MessageBox(self._view.root, semi_automated_step.message, ui_labels.USER_INTERACTION_NEEDED, [DialogOptions.PROCEED])
            await msg_box.wait_for_answer()
        elif semi_automated_step.interaction == TestInteraction.VALIDATION:
            msg_box = MessageBox(self._view.root, semi_automated_step.message, ui_labels.USER_INTERACTION_NEEDED, [DialogOptions.YES, DialogOptions.NO])
            answer = await msg_box.wait_for_answer()
            did_test_pass =  answer == DialogOptions.YES
            test.test_result = TestResult(did_test_pass, ui_labels.SUCCESS if did_test_pass else ui_labels.FAILURE)
        else:
            raise NotImplementedError("This user interaction type was not implemented")

        self._test_executor.proceed_semi_automated_test()

    def on_execution_state_changed(self, e: PropertyChangeEvent) -> None:
        execution_state: ExecutionState = e.new_value.execution_state
        enabled = execution_state != ExecutionState.NOT_RESPONSIVE
        for test_widget in self._test_widgets:
            test_widget.enable(enabled)


class DiagnosticsWindow(DeviceWindow):
    def __init__(self, device: SonicDevice, root, connection_name: str):
        self._logger: logging.Logger = logging.getLogger(connection_name + ".ui")
        try:
            self._device = device
            self._view = DeviceWindowView(root=root, title=f"Device Window - Diagnostics Tool - {connection_name}")
            super().__init__(self._logger, self._view, self._device.communicator)

            self._serialmonitor = SerialMonitor(self, self._device.communicator)
            self._logging = Logging(self, connection_name)
            self._test_executor = TestExecutor(self._device)
            self._testing_tab = HwTestingTab(self, self._test_executor)

            self._view.add_tab_views([
                self._testing_tab.view,
                self._serialmonitor.view,
            ], right_one=False)
            self._view.add_tab_views([
                self._logging.view
            ], right_one=True)

            self.app_state.subscribe_property_listener(AppState.APP_EXECUTION_CONTEXT_PROP_NAME, self._serialmonitor.on_execution_state_changed)
            self.app_state.subscribe_property_listener(AppState.APP_EXECUTION_CONTEXT_PROP_NAME, self._testing_tab.on_execution_state_changed)

        except Exception as e:
            self._logger.error(e)
            MessageBox.show_error(root, str(e))
            raise


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
        self._scroll_frame = ScrolledFrame(self)
        self._test_frame = ttk.Frame(self._scroll_frame)

    def _initialize_publish(self) -> None:
        self._scroll_frame.pack(fill=ttk.BOTH, expand=True, padx=sizes.MEDIUM_PADDING, pady=sizes.MEDIUM_PADDING)
        self._test_frame.pack(fill=ttk.BOTH, expand=True, padx=sizes.LARGE_PADDING, pady=sizes.LARGE_PADDING)

    @property
    def tests_frame(self) -> View:
        return self._test_frame # type: ignore
