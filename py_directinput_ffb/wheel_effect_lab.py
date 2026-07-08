from __future__ import annotations

import json
import math
import textwrap
import time

from dataclasses import dataclass
from pathlib import Path

from directinput_ffb.dinput_definitions import (
    C,
    DIJOYSTATE,
    DIDFT_AXIS,
    DIDFT_FFACTUATOR,
    DIJOFS_X,
    DIEFF_CARTESIAN,
    GUID_ConstantForce,
    GUID_Damper,
    GUID_Sine,
    GUID_Spring,
    INFINITE_EFFECT_DURATION,
)
from directinput_ffb import (
    acquire,
    create_constant_force_effect,
    create_damper_effect,
    create_device,
    create_direct_input,
    create_sine_effect,
    create_spring_effect,
    enum_device_objects,
    enum_devices,
    enum_effects,
    get_axis_logical_range,
    set_axis_range,
    set_cooperative_level,
    set_data_format,
    unacquire,
)


DEVICE_INDEX = 0
LOOP_HZ = 60
MAX_FORCE = 10000
FORCE_SIGN = 1
SCENE_BODY_PATH = Path(__file__).with_name("generated_scene_body.py")
STOP_REQUEST_PATH = Path(__file__).with_name(".wheel_stop_request")
WHEEL_STATE_PATH = Path(__file__).with_name("wheel_state.json")
SCENE_RELOAD_INTERVAL = 0.25
STATE_WRITE_INTERVAL = 1 / 30


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clamp_force(value: float, limit: int = MAX_FORCE) -> int:
    return int(round(clamp(value, -limit, limit)))


def guid_text(guid) -> str:
    return str(guid).lower()


def first_number(*values, default: float = 0.0) -> float:
    for value in values:
        if value is not None:
            return value
    return default


@dataclass
class WheelState:
    t: float
    dt: float
    raw_x: int
    x: float
    x_velocity: float


@dataclass
class Effects:
    constant_effect: object | None
    sine_effect: object | None
    spring_effect: object | None
    damper_effect: object | None

    last_constant: int = 0
    last_sine: int = 0
    last_spring: int = 0
    last_damper: int = 0

    def all_handles(self) -> list[object]:
        return [
            effect
            for effect in (
                self.constant_effect,
                self.sine_effect,
                self.spring_effect,
                self.damper_effect,
            )
            if effect is not None
        ]

    def start_all(self) -> None:
        for effect in self.all_handles():
            effect.download()
            effect.start(iterations=1)

    def stop_all(self) -> None:
        self.constant(0)
        self.sine(0)
        self.spring(0)
        self.damper(0)

        for effect in self.all_handles():
            try:
                effect.stop()
            except Exception:
                pass
            try:
                effect.unload()
            except Exception:
                pass

    def constant(
        self,
        magnitude: float | None = None,
        *,
        value: float | None = None,
        force: float | None = None,
        limit: int = MAX_FORCE,
        **_ignored,
    ) -> None:
        magnitude = first_number(magnitude, value, force)
        self.last_constant = clamp_force(FORCE_SIGN * magnitude, limit)
        if self.constant_effect is not None:
            self.constant_effect.set_magnitude(self.last_constant)

    def sine(
        self,
        magnitude: float | None = None,
        period_us: int | None = 55_000,
        *,
        value: float | None = None,
        period: int | None = None,
        period_ms: int | None = None,
        limit: int = MAX_FORCE,
        **_ignored,
    ) -> None:
        magnitude = first_number(magnitude, value)
        if period_ms is not None:
            period_us = int(period_ms * 1000)
        period_us = int(first_number(period_us, period, default=55_000))

        self.last_sine = abs(clamp_force(magnitude, limit))
        if self.sine_effect is not None:
            period_us = max(1_000, int(period_us))
            self.sine_effect.set_periodic(magnitude=self.last_sine, period_us=period_us)

    def spring(
        self,
        coefficient: float | None = None,
        saturation: int = 6000,
        dead_band: int = 250,
        *,
        value: float | None = None,
        strength: float | None = None,
        **_ignored,
    ) -> None:
        coefficient = first_number(coefficient, value, strength)
        self.last_spring = abs(clamp_force(coefficient, 10_000))
        if self.spring_effect is not None:
            self.spring_effect.set_condition(
                0,
                positive_coefficient=self.last_spring,
                negative_coefficient=self.last_spring,
                positive_saturation=saturation,
                negative_saturation=saturation,
                dead_band=dead_band,
            )

    def damper(
        self,
        coefficient: float | None = None,
        saturation: int = 6000,
        dead_band: int = 0,
        *,
        value: float | None = None,
        strength: float | None = None,
        **_ignored,
    ) -> None:
        coefficient = first_number(coefficient, value, strength)
        self.last_damper = abs(clamp_force(coefficient, 10_000))
        if self.damper_effect is not None:
            self.damper_effect.set_condition(
                0,
                positive_coefficient=self.last_damper,
                negative_coefficient=self.last_damper,
                positive_saturation=saturation,
                negative_saturation=saturation,
                dead_band=dead_band,
            )


def stop_effects(fx: Effects) -> None:
    fx.constant(0)
    fx.sine(0)
    fx.spring(0)
    fx.damper(0)


def default_update_effects(state: WheelState, fx: Effects) -> None:
    if state.t < 3.0:
        fx.constant(500)
    else:
        fx.constant(0)

    fx.sine(0)
    fx.spring(0)
    fx.damper(0)


class SceneBodyRunner:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.update_fn = None
        self.mtime_ns = None
        self.next_check_t = 0.0

    def run(self, state: WheelState, fx: Effects) -> bool:
        self._maybe_reload(state.t)
        if self.update_fn is None:
            return False

        try:
            self.update_fn(state, fx)
        except Exception as exc:
            print(f"\nScene runtime error: {exc}")
            self.update_fn = None
            stop_effects(fx)
            return True

        return True

    def _maybe_reload(self, t: float) -> None:
        if t < self.next_check_t:
            return
        self.next_check_t = t + SCENE_RELOAD_INTERVAL

        if not self.path.exists():
            self.update_fn = None
            self.mtime_ns = None
            return

        mtime_ns = self.path.stat().st_mtime_ns
        if mtime_ns == self.mtime_ns:
            return

        try:
            self.update_fn = self._compile_body(self.path.read_text(encoding="utf-8"))
            self.mtime_ns = mtime_ns
            print(f"\nLoaded scene body: {self.path.name}")
        except Exception as exc:
            print(f"\nScene compile error: {exc}")
            self.update_fn = None
            self.mtime_ns = mtime_ns

    def _compile_body(self, source: str):
        body = textwrap.dedent(source).strip("\n")
        if not body.strip():
            body = "pass"

        wrapped_source = (
            "def __scene_update(state, fx):\n"
            f"{textwrap.indent(body, '    ')}\n"
            "    pass\n"
        )
        env = {
            "__builtins__": {
                "abs": abs,
                "float": float,
                "int": int,
                "max": max,
                "min": min,
                "print": print,
                "round": round,
            },
            "clamp": clamp,
            "clamp_force": clamp_force,
            "math": math,
        }
        exec(compile(wrapped_source, str(self.path), "exec"), env)
        return env["__scene_update"]


SCENE_RUNNER = SceneBodyRunner(SCENE_BODY_PATH)


def update_effects(state: WheelState, fx: Effects) -> None:
    if SCENE_RUNNER.run(state, fx):
        return
    default_update_effects(state, fx)


def choose_ffb_axis(device) -> tuple[int, ...]:
    obj_infos = enum_device_objects(device, DIDFT_AXIS | DIDFT_FFACTUATOR)

    print("Force-feedback actuator axes:")
    for obj_info in obj_infos:
        print(f"  offset={obj_info.offset:>2} name={obj_info.name}")

    ffb_axis_offsets = tuple(
        obj_info.offset
        for obj_info in obj_infos
        if obj_info.is_axis and obj_info.is_ff_actuator
    )
    if not ffb_axis_offsets:
        raise RuntimeError("No force-feedback actuator axes found.")

    if DIJOFS_X in ffb_axis_offsets:
        return (DIJOFS_X,)
    return (ffb_axis_offsets[0],)


def create_effects(device, axes_offsets: tuple[int, ...]) -> Effects:
    supported = {guid_text(effect.guid) for effect in enum_effects(device)}

    def has(guid) -> bool:
        return guid_text(guid) in supported

    constant_effect = None
    sine_effect = None
    spring_effect = None
    damper_effect = None

    if has(GUID_ConstantForce):
        constant_effect = create_constant_force_effect(
            device,
            magnitude=0,
            direction_hundredths_deg=9000,
            direction_basis=DIEFF_CARTESIAN,
            duration_us=INFINITE_EFFECT_DURATION,
            axes_offsets=axes_offsets,
        )

    if has(GUID_Sine):
        sine_effect = create_sine_effect(
            device,
            magnitude=0,
            offset=0,
            phase_hundredths_deg=0,
            period_us=55_000,
            direction_hundredths_deg=9000,
            direction_basis=DIEFF_CARTESIAN,
            duration_us=INFINITE_EFFECT_DURATION,
            axes_offsets=axes_offsets,
        )

    if has(GUID_Spring):
        spring_effect = create_spring_effect(
            device,
            positive_coefficient=0,
            negative_coefficient=0,
            positive_saturation=6000,
            negative_saturation=6000,
            dead_band=250,
            offset=0,
            direction_basis=DIEFF_CARTESIAN,
            axes_offsets=axes_offsets,
        )

    if has(GUID_Damper):
        damper_effect = create_damper_effect(
            device,
            positive_coefficient=0,
            negative_coefficient=0,
            positive_saturation=6000,
            negative_saturation=6000,
            dead_band=0,
            offset=0,
            direction_basis=DIEFF_CARTESIAN,
            axes_offsets=axes_offsets,
        )

    return Effects(
        constant_effect=constant_effect,
        sine_effect=sine_effect,
        spring_effect=spring_effect,
        damper_effect=damper_effect,
    )


def read_wheel_state(device, axis_min: int, axis_max: int, start_time: float, last: WheelState | None) -> WheelState:
    dev_state = DIJOYSTATE()
    device.Poll()
    device.GetDeviceState(C.sizeof(DIJOYSTATE), C.byref(dev_state))

    now = time.perf_counter()
    t = now - start_time
    dt = 1 / LOOP_HZ if last is None else max(0.001, now - (start_time + last.t))

    axis_center = (axis_min + axis_max) / 2
    axis_half_span = (axis_max - axis_min) / 2
    x = clamp((dev_state.lX - axis_center) / axis_half_span, -1.0, 1.0)
    x_velocity = 0.0 if last is None else (x - last.x) / dt

    return WheelState(
        t=t,
        dt=dt,
        raw_x=int(dev_state.lX),
        x=float(x),
        x_velocity=float(x_velocity),
    )


def clear_stop_request() -> None:
    try:
        STOP_REQUEST_PATH.unlink()
    except FileNotFoundError:
        pass


def write_wheel_state(state: WheelState | None, effects: Effects | None, *, running: bool) -> None:
    payload = {
        "running": running,
        "x": 0.0 if state is None else state.x,
        "x_velocity": 0.0 if state is None else state.x_velocity,
        "raw_x": 0 if state is None else state.raw_x,
        "constant": 0 if effects is None else effects.last_constant,
        "sine": 0 if effects is None else effects.last_sine,
        "spring": 0 if effects is None else effects.last_spring,
        "damper": 0 if effects is None else effects.last_damper,
    }
    temp_path = WHEEL_STATE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload), encoding="utf-8")
    temp_path.replace(WHEEL_STATE_PATH)


def main() -> None:
    clear_stop_request()
    write_wheel_state(None, None, running=False)

    direct_input = create_direct_input()
    devices = enum_devices(direct_input, only_attached=True, only_force_feedback=True)
    if not devices:
        raise RuntimeError("No attached force-feedback game controllers found.")

    print("Devices:")
    for index, device_info in enumerate(devices):
        print(f"  [{index}] {device_info.product_name} / {device_info.instance_name}")

    device_info = devices[DEVICE_INDEX]
    print(f"Opening: {device_info.product_name}")
    device = create_device(direct_input, device_info.guid_instance)

    hwnd = set_cooperative_level(device)
    data_format = set_data_format(device)
    axes_offsets = choose_ffb_axis(device)
    print(f"Using FFB axis offsets: {axes_offsets}")

    axis_min, axis_max = get_axis_logical_range(device, axes_offsets[0])
    print(f"X logical range: [{axis_min}, {axis_max}]")
    set_axis_range(device, axes_offsets[0], axis_min, axis_max)

    effects = None
    acquired = False
    try:
        acquire(device)
        acquired = True

        effects = create_effects(device, axes_offsets)
        effects.start_all()
        print("Running. Press Ctrl+C to stop.")

        start_time = time.perf_counter()
        last_state = None
        last_print = 0.0
        last_state_write = 0.0

        while True:
            if STOP_REQUEST_PATH.exists():
                print("\nStop requested by GUI.")
                break

            state = read_wheel_state(device, axis_min, axis_max, start_time, last_state)
            update_effects(state, effects)
            last_state = state

            if state.t - last_state_write > STATE_WRITE_INTERVAL:
                last_state_write = state.t
                write_wheel_state(state, effects, running=True)

            if state.t - last_print > 0.25:
                last_print = state.t
                print(
                    f"\rx={state.x:+.3f} "
                    f"v={state.x_velocity:+.2f} "
                    f"constant={effects.last_constant:+5d} "
                    f"sine={effects.last_sine:4d} "
                    f"spring={effects.last_spring:4d} "
                    f"damper={effects.last_damper:4d}",
                    end="",
                    flush=True,
                )

            time.sleep(1 / LOOP_HZ)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if effects is not None:
            effects.stop_all()
        if acquired:
            unacquire(device)
        write_wheel_state(None, None, running=False)
        clear_stop_request()
        _ = hwnd
        _ = data_format
        print("Done.")


if __name__ == "__main__":
    main()
