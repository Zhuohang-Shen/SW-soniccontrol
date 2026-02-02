import attrs
from sonic_protocol.protocols.protocol_v3_0_0.types.types import TestInteraction
from soniccontrol.events import EventManager, PropertyChangeEvent

@attrs.define()
class TestResult:
    success: bool = attrs.field()
    assertion_msg: str = attrs.field(factory=str)

@attrs.define()
class SemiAutomatedStep:
    interaction: TestInteraction = attrs.field()
    message: str = attrs.field()


def _emit_is_running_changed_event(self, attr: attrs.Attribute, value):
    old_value = getattr(self, attr.name)

    if value != old_value:
        self.emit(PropertyChangeEvent("is_running", old_value, value))

    return value

@attrs.define()
class TestInfo(EventManager):
    index: int = attrs.field()
    name: str = attrs.field()
    suite_name: str = attrs.field()
    is_running: bool = attrs.field(init=False, default=False, on_setattr=_emit_is_running_changed_event)
    test_result: TestResult | None = attrs.field(init=False, default=None)
