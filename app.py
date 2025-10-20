"""Flask application providing remote control over the Raspberry Pi smart light."""
from __future__ import annotations

import logging
import os
from typing import Dict

from flask import Flask, render_template, request

from rpilight.controller import LightController, build_default_controller

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class ApplicationFactory:
    """Factory that encapsulates controller lifetime management."""

    def __init__(self) -> None:
        self._controller: LightController | None = None

    def create_app(self) -> Flask:
        app = Flask(__name__, template_folder="rpilight/templates", static_folder="rpilight/static")

        @app.before_first_request
        def _init_controller() -> None:
            if self._controller is None:
                self._controller = build_default_controller(
                    use_gpio=os.environ.get("USE_GPIO", "0") == "1",
                    relay_pin=int(os.environ.get("RELAY_PIN", 17)),
                    sensor_pin=int(os.environ["SENSOR_PIN"]) if "SENSOR_PIN" in os.environ else None,
                    darkness_threshold=float(os.environ.get("DARKNESS_THRESHOLD", 0.3)),
                )

        @app.route("/")
        def index() -> str:
            return render_template("index.html")

        @app.get("/api/status")
        def api_status() -> Dict[str, object]:
            controller = self._require_controller()
            sensor_value = controller.last_sensor_value
            return {
                "auto": controller.auto_enabled,
                "is_on": controller.is_on,
                "sensor_value": sensor_value,
                "darkness_threshold": controller.darkness_threshold,
            }

        @app.post("/api/auto")
        def api_auto() -> Dict[str, object]:
            controller = self._require_controller()
            payload = request.get_json(silent=True) or {}
            enabled = bool(payload.get("enabled", True))
            controller.set_auto(enabled)
            return {"auto": controller.auto_enabled}

        @app.post("/api/manual")
        def api_manual() -> Dict[str, object]:
            controller = self._require_controller()
            payload = request.get_json(silent=True) or {}
            turn_on = bool(payload.get("turn_on", True))
            controller.set_manual(turn_on)
            return {"is_on": controller.is_on, "auto": controller.auto_enabled}

        @app.post("/api/threshold")
        def api_threshold() -> Dict[str, object]:
            controller = self._require_controller()
            payload = request.get_json(silent=True) or {}
            try:
                threshold = float(payload["value"])
            except (KeyError, TypeError, ValueError):
                return {"error": "Invalid threshold"}, 400
            controller.darkness_threshold = max(0.0, min(1.0, threshold))
            return {"darkness_threshold": controller.darkness_threshold}

        @app.get("/health")
        def health() -> Dict[str, str]:
            return {"status": "ok"}

        return app

    def _require_controller(self) -> LightController:
        if self._controller is None:
            raise RuntimeError("Controller has not been initialized")
        return self._controller


def main() -> None:
    factory = ApplicationFactory()
    app = factory.create_app()
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 8000))
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
