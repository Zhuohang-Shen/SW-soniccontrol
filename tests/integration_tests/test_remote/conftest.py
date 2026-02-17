import asyncio
from typing import Any, List, Tuple
import pytest
import pytest_asyncio
from sonic_protocol.schema import DeviceParamConstants
from soniccontrol import DeviceParamConstantType
from soniccontrol.communication.connection import CLIConnection, SerialConnection
from soniccontrol.remote_controller_v2 import RemoteController
from tests.integration_tests.conftest import Profile
import os
import shutil
from pathlib import Path


@pytest_asyncio.fixture(scope="function", autouse=True)
async def remote_controller(request):
    # setup
    plugin_config = request.config._sonic_control_plugin
    profile: Profile = plugin_config.profile
    url: str = plugin_config.url

    simulation_exe_path = Path(os.environ["FIRMWARE_BUILD_DIR_PATH"]) / "linux/platform_linux/src/device/device_main"

    # ensure all device_main processes are killed. Needed because they need access to the same port.

    connection = None
    match profile:
        case Profile.simulation_worker:
            cmd_args = ["--profile=worker", "--name=test_worker"]
            connection = CLIConnection(profile.name, simulation_exe_path, cmd_args=cmd_args)
        case Profile.simulation_descale:
            cmd_args = ["--profile=descale", "--name=test_descale"]
            connection = CLIConnection(profile.name, simulation_exe_path, cmd_args=cmd_args)
        case Profile.device_worker | Profile.device_descale:
            connection = SerialConnection(profile.name, url)
        case _:
            raise NotImplementedError(f"connection setup not implemented for profile {profile}")

    controller = await RemoteController.connect(connection)
    await controller.stop_updater()
    await controller.stop_running_processes()
    
    assert controller.is_connected, "Controller not connected to device"
    actual_device_type = controller.device_info.device_type
    assert actual_device_type == plugin_config.device_type, f"Expected to connect to a {actual_device_type} but instead connected to a {plugin_config.device_type}"

    # return
    yield controller

    # teardown
    await controller.disconnect()

    data_dir_path = Path(os.environ["FIRMWARE_BUILD_DIR_PATH"]).expanduser() / "../output/data"
    data_dir_path = data_dir_path.resolve()
    if profile == Profile.simulation_worker:
        shutil.rmtree(data_dir_path / "test_worker")
    elif profile == Profile.simulation_descale:
        shutil.rmtree(data_dir_path / "test_descale")


def format_command(command_fmt_str: str, *args, consts: DeviceParamConstants | None = None):    
    if args is None:
        return command_fmt_str
    
    if len(args) == 0:
        return command_fmt_str
    
    if consts is None:
        return command_fmt_str.format(*args)

    deduced_args = []
    for arg in args:
        deduced_arg = getattr(consts, arg.value) if isinstance(arg, DeviceParamConstantType) else arg
        deduced_args.append(deduced_arg)

    return command_fmt_str.format(*deduced_args)
    

@pytest.fixture(scope="function")
def formatted_command_str(request, remote_controller):
    command_fmt_str, args = request.param
    consts = remote_controller.protocol_consts

    if args is None:
        return command_fmt_str
    
    if not isinstance(args, list):
        args = [ args ]

    return format_command(command_fmt_str, *args, consts=consts)
