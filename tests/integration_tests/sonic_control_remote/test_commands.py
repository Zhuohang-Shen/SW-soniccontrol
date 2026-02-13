from typing import List

import attrs
from soniccontrol import DeviceParamConstantType, Answer, EFieldName, CommandCode
from .asserts import assert_answer, assert_answer_is_not_error
from tests.integration_tests.sonic_control_remote.conftest import format_command
import pytest
from pytest_check.context_manager import check
from sonic_robot.deduce_command_examples import deduce_command_examples
import allure
import json
from allure_commons.lifecycle import AllureLifecycle 
from allure_commons.model2 import Status, StatusDetails, TestStepResult

@pytest.mark.asyncio
@pytest.mark.parametrize("formatted_command_str", [
    ("!g={}", DeviceParamConstantType.MIN_GAIN),
    ("!gain={}", DeviceParamConstantType.MIN_GAIN),
    ("set_gain={}", DeviceParamConstantType.MIN_GAIN),
    ("-", None),
    ("get_update", None),
    ("?g", None),
    ("?gain", None),
    ("get_gain", None),
], indirect=True)
async def test_if_aliases_are_working(formatted_command_str, remote_controller):
    answer = await remote_controller.send_command(formatted_command_str)
    assert answer.valid, "Answer should be valid"

@pytest.mark.asyncio
async def test_if_gain_can_be_set_and_retrieved(remote_controller):
    consts = remote_controller.protocol_consts

    await remote_controller.send_command(format_command("!gain={}", consts.min_gain))
    answer = await remote_controller.send_command("?gain")
    assert_answer(answer, { EFieldName.GAIN: consts.min_gain })

    await remote_controller.send_command(format_command("!gain={}", consts.max_gain))
    answer = await remote_controller.send_command("?gain")
    assert_answer(answer, { EFieldName.GAIN: consts.max_gain })
    

@pytest.mark.asyncio
async def test_deduced_commands(remote_controller):
    @attrs.define()
    class DeducedCommandError(Exception):
        command: str = attrs.field()
        answer: Answer = attrs.field()
        step: int = attrs.field()
        assert_msg: str = attrs.field()

        def __str__(self) -> str:
            return f"Error on {self.step}-th command:\n" + \
                    f"'{self.command}' returned '{self.answer.message}'\n" + \
                    f"triggered assertion: '{self.assert_msg}'"


    info = remote_controller.device_info
    commands_to_skip = [
        CommandCode.SONIC_FORCE,
        CommandCode.GO_INTO_DEVICE_STATE,
        CommandCode.START_CONFIGURATOR,
        CommandCode.START_OPERATOR,
        CommandCode.START_DIAGNOSTIC_TOOL,
        CommandCode.RESTART_DEVICE,
        CommandCode.SET_FLASH_115200,
        CommandCode.SET_FLASH_9600,
        CommandCode.SET_FLASH_USB
    ]
    commands = deduce_command_examples(
        info.protocol_version, info.device_type, info.is_release, 
        skip_command_codes=commands_to_skip
    )

    num_commands = len(commands)
    errors = []
    for i, command in enumerate(commands):
        with allure.step(f"executing {i}/{num_commands}: '{command}'"):
            answer = await remote_controller.send_command(command)
            try:
                assert_answer_is_not_error(answer, errors_to_check=[
                    CommandCode.E_INTERNAL_DEVICE_ERROR, 
                    CommandCode.E_COMMAND_NOT_KNOWN, 
                    CommandCode.E_PARSING_ERROR, 
                    CommandCode.E_SYNTAX_ERROR
                ])
            except AssertionError as e:
                errors.append(DeducedCommandError(command, answer, i, str(e)))
                lifecycle = AllureLifecycle()
                lifecycle.update_step(
                    lambda step_result: step_result.update(
                        status=Status.FAILED,
                        statusDetails=StatusDetails(message=str(e))
                    )
                )

        await remote_controller.send_command("!log[global]=ERROR")
        await remote_controller.send_command("!stop")
        await remote_controller.send_command("!sonic_force")
        await remote_controller.send_command("!clear_errors")
        await remote_controller.send_command("!control_mode=remote")

    error_json = json.dumps([{ 
        "full_error_msg": str(e), 
        "index": e.step, 
        "command": e.command, 
        "answer": e.answer.message, 
        "assert_msg": e.assert_msg 
    } for e in errors ])
    allure.attach(
        error_json,
        attachment_type=allure.attachment_type.JSON
    )
    assert len(errors) == 0, "Errors occurred"
