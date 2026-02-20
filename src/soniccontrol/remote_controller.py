import asyncio
import logging
from os import environ
from pathlib import Path
from typing import Callable, Optional
import attrs

from sonic_protocol.python_parser.answer import Answer
from sonic_protocol.python_parser.commands import Command
from sonic_protocol.schema import DeviceType
from soniccontrol.app_config import PLATFORM, SOFTWARE_VERSION
from soniccontrol.builder import DeviceBuilder
from soniccontrol.communication.connection import CLIConnection, Connection
from soniccontrol.communication.postman_proxy_communicator import PostmanProxyCommunicator
from soniccontrol.communication.serial_communicator import SerialCommunicator
from soniccontrol.data_capturing.capture import Capture
from soniccontrol.data_capturing.capture_target import CaptureSpectrumArgs, CaptureSpectrumMeasure, CaptureTargets
from soniccontrol.data_capturing.experiment import Experiment, ExperimentMetaData
from soniccontrol.logging_utils import create_logger_for_connection
from soniccontrol.procedures.procedure import ProcedureArgs
from soniccontrol.procedures.procedure_controller import ProcedureController, ProcedureType
from soniccontrol.procedures.procs.spectrum_measure import SpectrumMeasureArgs
from soniccontrol.scripting.interpreter_engine import InterpreterEngine
from soniccontrol.scripting.new_scripting import NewScriptingFacade
from soniccontrol.sonic_device import SonicDevice
from soniccontrol.updater import Updater

@attrs.define()
class SpectrumArgsAdapter(CaptureSpectrumArgs):
    spectrum_args: SpectrumMeasureArgs = attrs.field() # type: ignore


class RemoteController:
    """
    This Remote Controller should in future replace the old one.
    It has minor improvements, because it follows more a RAII pattern, 
    making it also more suitable to use together with fixtures
    """

    def __init__(self, connection: Connection, device: SonicDevice, logger: logging.Logger):
        self._connection = connection
        self._device: SonicDevice = device
        self._logger = logger    
        self._updater: Updater = Updater(self._device)
        self._updater.start()
        self._proc_controller: ProcedureController = ProcedureController(self._device, updater=self._updater)
        self._scripting: NewScriptingFacade = NewScriptingFacade()

    @staticmethod
    async def connect(connection: Connection, log_path: Optional[Path]=None):
        logger = create_logger_for_connection(connection.connection_name, log_path if log_path is not None else Path("."))   

        device_builder = DeviceBuilder(logger=logger)

        communicator = SerialCommunicator(logger=logger) # type: ignore
        await communicator.open_communication(connection)
        device = await device_builder.build_amp(communicator)
        
        if device.info.device_type == DeviceType.POSTMAN:
            postman = device
            worker_communicator = PostmanProxyCommunicator(communicator)
            await worker_communicator.open_communication(connection)
            device = await device_builder.build_amp(worker_communicator)
            
            loop = asyncio.get_running_loop()
            worker_communicator.subscribe(
                communicator.DISCONNECTED_EVENT, 
                lambda _: loop.run_until_complete(postman.disconnect())
            )

        return RemoteController(connection, device, logger)

    def is_connected(self) -> bool:
        return self._device.communicator.connection_opened.is_set()

    def start_updater(self):
        if not self._updater.running.set():
            self._updater.start()

    """
    Note:   
        The updater is used by the procedure controller internally 
        to get information about if a procedure is running on the device.
        If you stop the updater, the procedure controller cannot detect anymore, when a procedure is finished and will run forever. 
        However you can manually pull an update over the updater and send that to the procedure controller or just
        call stop procedure.
    """
    async def stop_updater(self):
        if self._updater.running:
            await self._updater.stop()

    async def send_command(self, command: str | Command, raise_exception: bool = False) -> Answer:
        return await self._device.execute_command(command, raise_exception=raise_exception)
    
    async def get_update(self) -> Answer:
        return await self._device.get_update()
    
    async def stop_running_processes(self) -> None:
        await self._device.stop_running_processes()

    async def execute_script(self, text: str, callback: Callable[[str], None] = lambda _: None) -> None:
        runnable_script = self._scripting.parse_script(text)
        interpreter = InterpreterEngine(self._device, self._updater, self._logger)
        interpreter.subscribe_property_listener(InterpreterEngine.PROPERTY_CURRENT_TARGET, lambda target: callback(target.data.task))
        interpreter.script = runnable_script
        interpreter.start()
        await interpreter.wait_for_script_to_halt()

    def execute_procedure(self, procedure: ProcedureType, args: dict | ProcedureArgs, event_loop=asyncio.get_event_loop()) -> None:
        if isinstance(args, ProcedureArgs):
            procedure_args = args
        else:
            arg_class = self._proc_controller.proc_args_list[procedure]
            procedure_args = arg_class.from_dict(**args)

        self._proc_controller.execute_proc(procedure, procedure_args, event_loop)
        
    async def wait_for_procedure_to_finish(self):
        await self._proc_controller.wait_for_proc_to_finish()

    async def stop_procedure(self) -> None:
        await self._proc_controller.stop_proc()

    async def measure_spectrum(self, output_dir: Path, spectrum_args: SpectrumMeasureArgs, 
                               experiment_metadata: ExperimentMetaData, blocking: bool=True) -> None:
        capture = Capture(output_dir)
        capture_target = CaptureSpectrumMeasure(self._updater, self._proc_controller, SpectrumArgsAdapter(spectrum_args))
        self._updater.subscribe("update", lambda e: capture.on_update(e.data["status"]))

        experiment = Experiment(experiment_metadata, self._device.info,
                                 SOFTWARE_VERSION, PLATFORM.value, 
                                 CaptureTargets.SPECTRUM_MEASURE)

        await capture.start_capture(experiment, capture_target)
        if blocking:
            await capture.wait_for_capture_to_complete()

    async def disconnect(self) -> None:
        await self._updater.stop()
        await self._device.disconnect()

    async def reconnect(self) -> None:
        is_updater_running = self._updater.running.is_set()

        await self._updater.stop()
        await self._device.disconnect()

        await self._device.communicator.open_communication(self._connection)
        if is_updater_running:
            # restart after stopping
            self._updater.start()
    
    @property
    def updater(self):
        return self._updater
    
    @property 
    def protocol_consts(self):
        return self._device.protocol.consts
    
    @property
    def device_info(self): 
        return self._device.info



async def main():
    from soniccontrol.remote_controller import RemoteController
    import sonic_protocol.python_parser.commands as cmds
    from sonic_protocol.field_names import EFieldName

    #await controller.connect_via_serial(Path("/dev/ttyUSB0"))
    firmware_dir = environ.get('FIRMWARE_BUILD_DIR_PATH')
    if not firmware_dir:
        raise ValueError("Environment variable 'FIRMWARE_BUILD_DIR_PATH' is not set.")
    exe_path = firmware_dir + '/linux/platform_linux/src/device/device_main'
    connection = CLIConnection("simulation", Path(exe_path), [
        '--product-type=worker', 
        '--name=test_worker', 
        '--port=4000', 
        f'--data-dir={firmware_dir + "/data"}'
    ])

    controller = await RemoteController.connect(connection)

    # it is allowed but discouraged to send strings
    await controller.send_command("?protocol")

    # use instead the cmds classes. Avoids typos and will stay compatible with future protocols
    await controller.send_command(cmds.GetProtocol())
    answer = await controller.send_command(cmds.SetAtf(1, 100000))
    
    print(answer.message)
    if answer.valid:
        print(answer.field_value_dict[EFieldName.ATF])

    await controller.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
