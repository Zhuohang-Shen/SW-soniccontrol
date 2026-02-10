import pytest
import pytest_asyncio
from soniccontrol.communication.connection import CLIConnection, SerialConnection
from soniccontrol.remote_controller_v2 import RemoteController
from .conftest import Profile
import os
from pathlib import Path


@pytest_asyncio.fixture(scope="session")
async def remote_controller(request):
    # setup
    profile = Profile(request.config.getoption("--profile"))
    url = request.config.getoption("--url")

    simulation_exe_path = Path(os.environ["FIRMWARE_BUILD_DIR_PATH"]) / "linux/platform_linux/src/device/device_main"

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

    controller = await RemoteController.connect(connection)

    # return
    yield controller

    # teardown
    await controller.disconnect()

    data_dir_path = Path(os.environ["FIRMWARE_BUILD_DIR_PATH"]) / "output"
    if profile == Profile.simulation_worker:
        os.rmdir(data_dir_path / "test_worker")
    elif profile == Profile.simulation_descale:
        os.rmdir(data_dir_path / "test_descale")

