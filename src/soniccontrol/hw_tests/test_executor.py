import asyncio
from typing import List

from sonic_protocol.field_names import EFieldName
from sonic_protocol.protocols.protocol_v3_0_0.types.types import TestResult as ProtocolTestResult
from soniccontrol.events import Event, EventManager, PropertyChangeEvent
from .test_base import SemiAutomatedStep, TestInfo, TestResult
from soniccontrol.sonic_device import SonicDevice
import sonic_protocol.python_parser.commands as commands


class TestExecutionException(Exception):
    pass


class TestExecutor(EventManager):
    NEEDS_USER_INTERACTION_EVENT: str = "NEEDS_USER_INTERACTION_EVENT"
    RUNNING_TEST_INDEX_PROPERTY: str = "RUNNING_TEST_INDEX"

    def __init__(self, device: SonicDevice):
        self._device = device
        self._run_test_task: asyncio.Task | None = None
        self._running_test_index: int | None = None  # either index of running test or none if no test is running

    @property 
    def running_test_index(self) -> int | None:
        return self._running_test_index

    def _set_running_test_index(self, new_value: int | None):
        old_value = self._running_test_index
        self._running_test_index = new_value
        if old_value != new_value:
            self.emit(PropertyChangeEvent(TestExecutor.RUNNING_TEST_INDEX_PROPERTY, old_value, new_value))

    async def load_tests(self) -> List[TestInfo]:
        if not self._device.has_command(commands.GetNumTests()):
            raise TestExecutionException("cannot load tests for this device, the protocol is too old and does not support the testing feature")

        answer_num_tests = await self._device.execute_command(commands.GetNumTests())
        num_tests = answer_num_tests.field_value_dict[EFieldName.COUNT]

        tests: List[TestInfo] = []
        for i in range(num_tests):
            answer_test_info = await self._device.execute_command(commands.GetTestInfo(i))
            test_name = answer_test_info.field_value_dict[EFieldName.TEST_NAME]
            test_suite_name = answer_test_info.field_value_dict[EFieldName.TEST_SUITE_NAME]
            tests.append(TestInfo(i, test_name, test_suite_name))
        return tests

    def run_test(self, test: TestInfo):
        if self._run_test_task is not None and not self._run_test_task.done():
            raise TestExecutionException("There is already a Test executing") 

        self._run_test_task = asyncio.create_task(self._run_test(test))

    async def stop_test(self):
        if self._run_test_task is not None:
            self._run_test_task.cancel()
            await self._run_test_task

    async def _run_test(self, test: TestInfo):
        try:
            test.test_result = None
            self._set_running_test_index(test.index)

            while True:
                answer = await self._device.execute_command(commands.RunTest(test.index))

                test_result_value = answer.field_value_dict[EFieldName.TEST_RESULT]
                interaction_type = answer.field_value_dict[EFieldName.TEST_INTERACTION]
                msg = answer.field_value_dict[EFieldName.MESSAGE]

                if test_result_value != ProtocolTestResult.SEMI_AUTOMATED_STEP:
                    test.test_result = TestResult(test_result_value == ProtocolTestResult.SUCCESS, msg)
                    break

                self.emit(Event(
                    TestExecutor.NEEDS_USER_INTERACTION_EVENT, 
                    semi_automated_step=SemiAutomatedStep(interaction_type, msg)
                ))
        except asyncio.CancelledError:
            # TODO: abort test
            pass 
        except Exception as e:
            raise
        finally:
            self._set_running_test_index(None)
