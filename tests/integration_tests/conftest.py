from enum import Enum, auto


class Profile(Enum):
    simulation_worker = auto()
    simulation_descale = auto()
    device_worker = auto()
    device_descale = auto()


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
        help="Choose the url for the serial port over that the device is connected",
    )
