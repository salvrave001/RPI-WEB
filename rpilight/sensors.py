"""Sensor abstractions for the Raspberry Pi smart light project."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, time as dt_time
from typing import Optional

logger = logging.getLogger(__name__)


class AmbientLightSensor(ABC):
    """Abstract sensor returning a normalized light level (0-1)."""

    @abstractmethod
    def read(self) -> float:
        """Return current light level (0 = dark, 1 = bright)."""


class GPIONativeLightSensor(AmbientLightSensor):
    """Light sensor using gpiozero's LightSensor helper."""

    def __init__(self, pin: int, *, threshold: float = 0.5) -> None:
        try:
            from gpiozero import LightSensor
        except (ModuleNotFoundError, ImportError) as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "gpiozero is required for GPIONativeLightSensor but could not be imported"
            ) from exc

        self._sensor = LightSensor(pin, threshold=threshold)

    def read(self) -> float:
        value = 1.0 - float(self._sensor.value)
        logger.debug("GPIO light sensor value: %s", value)
        return value


class TimeOfDaySensor(AmbientLightSensor):
    """Virtual sensor that reports darkness based on configured time windows."""

    def __init__(
        self,
        *,
        evening_time: dt_time,
        morning_time: dt_time,
    ) -> None:
        self.evening_time = evening_time
        self.morning_time = morning_time

    def read(self) -> float:
        now = datetime.now().time()
        is_dark = self._is_dark(now)
        logger.debug("TimeOfDaySensor: now=%s dark=%s", now, is_dark)
        return 0.0 if is_dark else 1.0

    def _is_dark(self, current: dt_time) -> bool:
        if self.evening_time < self.morning_time:
            return self.evening_time <= current <= self.morning_time
        return current >= self.evening_time or current <= self.morning_time


class FixedValueSensor(AmbientLightSensor):
    """Simple sensor returning a predetermined value (useful for testing)."""

    def __init__(self, value: float) -> None:
        self._value = value

    def read(self) -> float:
        return self._value
