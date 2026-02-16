from enum import Enum, auto
from typing import List
import attrs
from sonic_protocol.schema import DeviceType
import pytest


class Profile(Enum):
    simulation_worker = auto()
    simulation_descale = auto()
    device_worker = auto()
    device_descale = auto()

@attrs.define()
class SonicControlPlugin:
    profile: Profile = attrs.field()
    url: str | None = attrs.field()
    device_type: DeviceType = attrs.field()


def pytest_addoption(parser):
    parser.addoption(
        "--profile",
        action="store",
        default=Profile.simulation_worker.name,
        choices=(profile.name for profile in Profile),
        help="Choose a profile to execute",
    )
    parser.addoption(
        "--url",
        action="store",
        default=None,
        help="Choose the url for the serial port over that the device is connected",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "allowed_devices(*device_list): mark test to run only for certain selected devices",
    )

    profile = Profile[config.getoption("--profile")]
    url = config.getoption("--url")
    device = None

    match profile:
        case Profile.simulation_descale | Profile.device_descale:
            device = DeviceType.DESCALE
        case Profile.simulation_worker | Profile.device_worker:
            device = DeviceType.MVP_WORKER
        case _:
            raise NotImplementedError("This profile is not supported")

    config._sonic_control_plugin = SonicControlPlugin(profile, url, device)


def pytest_runtest_setup(item):
    allowed_devices: List[DeviceType] = [ 
        arg 
        for mark in item.iter_markers(name="allowed_devices") 
        for arg in mark.args
    ]
    if len(allowed_devices) == 0:
        return 
    
    device_type = item.config._sonic_control_plugin.device_type
    if device_type not in allowed_devices:
        pytest.skip(f"The device type {device_type.name} is not supported for this test")
