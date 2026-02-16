import pytest
import pytest_asyncio

from .asserts import assert_answer, send_command_and_check_response
from soniccontrol import EFieldName, commands


@pytest.mark.asyncio
async def test_if_devices_saves_transducer_state(remote_controller):
    frequency = 123456
    gain = 96
    await send_command_and_check_response(remote_controller, commands.SetFrequency(frequency))
    await send_command_and_check_response(remote_controller, commands.SetGain(gain))

    await remote_controller.disconnect()
    await remote_controller.reconnect()

    answer = await remote_controller.send_command(commands.GetUpdate())
    assert_answer(answer, { EFieldName.FREQUENCY: frequency, EFieldName.GAIN: gain })
