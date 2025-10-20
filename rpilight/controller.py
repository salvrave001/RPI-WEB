"""Core lighting controller logic for Raspberry Pi smart light project."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import time as dt_time
from typing import Callable, Optional

from .sensors import AmbientLightSensor, TimeOfDaySensor

logger = logging.getLogger(__name__)


class LightHardwareInterface:
    """Abstraction over the underlying light switching hardware."""

    def __init__(self, *, on_func: Callable[[], None], off_func: Callable[[], None]):
        self._on_func = on_func
        self._off_func = off_func
        self._state = False

    @property
    def is_on(self) -> bool:
        return self._state

    def turn_on(self) -> None:
        logger.debug("Turning light on via hardware interface")
        self._on_func()
        self._state = True

    def turn_off(self) -> None:
        logger.debug("Turning light off via hardware interface")
        self._off_func()
        self._state = False


class DummyHardware(LightHardwareInterface):
    """Fallback hardware controller used when GPIO is unavailable."""

    def __init__(self) -> None:
        def _noop_on() -> None:
            logger.info("Dummy hardware: ON")

        def _noop_off() -> None:
            logger.info("Dummy hardware: OFF")

        super().__init__(on_func=_noop_on, off_func=_noop_off)


class GPIOHardware(LightHardwareInterface):
    """Hardware interface using gpiozero for Raspberry Pi."""

    def __init__(self, *, pin: int):
        try:
            from gpiozero import OutputDevice
        except (ModuleNotFoundError, ImportError) as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "gpiozero is required for GPIOHardware but could not be imported"
            ) from exc

        device = OutputDevice(pin)
        super().__init__(on_func=device.on, off_func=device.off)


@dataclass
class LightController:
    """Encapsulates auto/manual light control logic."""

    hardware: LightHardwareInterface
    sensor: Optional[AmbientLightSensor] = None
    poll_interval: float = 5.0
    darkness_threshold: float = 0.3
    auto_enabled: bool = True
    _thread: threading.Thread = field(init=False, repr=False)
    _stop_event: threading.Event = field(init=False, repr=False)
    _last_sensor_value: Optional[float] = field(default=None, init=False)

    def __post_init__(self) -> None:
        logger.debug("Initializing LightController")
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        logger.debug("LightController background loop started")
        while not self._stop_event.is_set():
            if self.auto_enabled and self.sensor is not None:
                try:
                    value = self.sensor.read()
                    self._last_sensor_value = value
                    logger.debug("Sensor reading: %s", value)
                    if value <= self.darkness_threshold:
                        self.hardware.turn_on()
                    else:
                        self.hardware.turn_off()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception("Error reading sensor: %s", exc)
            time.sleep(self.poll_interval)
        logger.debug("LightController background loop stopped")

    def shutdown(self) -> None:
        logger.debug("Shutting down LightController")
        self._stop_event.set()
        self._thread.join(timeout=self.poll_interval * 2)

    def set_auto(self, enabled: bool) -> None:
        logger.info("Auto mode set to %s", enabled)
        self.auto_enabled = enabled

    def set_manual(self, on: bool) -> None:
        logger.info("Manual set to %s", on)
        self.auto_enabled = False
        if on:
            self.hardware.turn_on()
        else:
            self.hardware.turn_off()

    @property
    def is_on(self) -> bool:
        return self.hardware.is_on

    @property
    def last_sensor_value(self) -> Optional[float]:
        return self._last_sensor_value


def build_default_controller(
    *,
    use_gpio: bool,
    relay_pin: int = 17,
    sensor_pin: Optional[int] = None,
    darkness_threshold: float = 0.3,
    evening_time: dt_time = dt_time(21, 0),
    morning_time: dt_time = dt_time(6, 0),
) -> LightController:
    """Factory helper that configures controller with sensible defaults."""

    if use_gpio:
        try:
            hardware: LightHardwareInterface = GPIOHardware(pin=relay_pin)
        except RuntimeError as exc:
            logger.warning("Falling back to dummy hardware: %s", exc)
            hardware = DummyHardware()
    else:
        hardware = DummyHardware()

    if sensor_pin is not None:
        from .sensors import GPIONativeLightSensor

        sensor: AmbientLightSensor = GPIONativeLightSensor(pin=sensor_pin)
    else:
        sensor = TimeOfDaySensor(evening_time=evening_time, morning_time=morning_time)

    return LightController(
        hardware=hardware,
        sensor=sensor,
        darkness_threshold=darkness_threshold,
    )
