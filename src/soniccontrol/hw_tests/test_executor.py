import asyncio
from typing import List

from sonic_protocol.field_names import EFieldName
from sonic_protocol.protocols.protocol_v3_0_0.types.types import TestResult as ProtocolTestResult
from soniccontrol.events import Event, EventManager
from .test_base import SemiAutomatedStep, TestInfo, TestResult
from soniccontrol.sonic_device import SonicDevice
import sonic_protocol.python_parser.commands as commands


class TestExecutionException(Exception):
    pass

class TestExecutor(EventManager):
    NEEDS_USER_INTERACTION_EVENT: str = "NEEDS_USER_INTERACTION_EVENT"

    def __init__(self, device: SonicDevice):
        self._device = device
        self._run_test_task: asyncio.Task | None = None

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
        test.is_running = True
        try:
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
            test.is_running = False
