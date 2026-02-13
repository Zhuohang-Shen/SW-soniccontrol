from sonic_protocol.command_codes import CommandCode
from sonic_protocol.field_names import EFieldName
from soniccontrol import DeviceParamConstantType
from .asserts import assert_answer, assert_answer_is_not_error
from tests.integration_tests.sonic_control_remote.conftest import format_command
import pytest
from pytest_check.context_manager import check
from sonic_robot.deduce_command_examples import deduce_command_examples
import allure


@allure.title("Test aliases")
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

@allure.title("Test set and get")
@pytest.mark.asyncio
async def test_if_gain_can_be_set_and_retrieved(remote_controller):
    consts = remote_controller.protocol_consts

    await remote_controller.send_command(format_command("!gain={}", consts.min_gain))
    answer = await remote_controller.send_command("?gain")
    assert_answer(answer, { EFieldName.GAIN: consts.min_gain })

    await remote_controller.send_command(format_command("!gain={}", consts.max_gain))
    answer = await remote_controller.send_command("?gain")
    assert_answer(answer, { EFieldName.GAIN: consts.max_gain })

@allure.title("Test deduced commands")
@pytest.mark.asyncio
async def test_deduced_commands(remote_controller):
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
    
    for command in commands:
        answer = await remote_controller.send_command(command)
        
        with check:
            assert_answer_is_not_error(answer, errors_to_check=[
                CommandCode.E_INTERNAL_DEVICE_ERROR, 
                CommandCode.E_COMMAND_NOT_KNOWN, 
                CommandCode.E_PARSING_ERROR, 
                CommandCode.E_SYNTAX_ERROR
            ])
        await remote_controller.send_command("!log[global]=ERROR")
        await remote_controller.send_command("!stop")
        await remote_controller.send_command("!sonic_force")
        await remote_controller.send_command("!clear_errors")
        await remote_controller.send_command("!control_mode=remote")
