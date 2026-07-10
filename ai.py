import base64
import mimetypes
import os
import re
import textwrap
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT_DIR / "output.txt"
SCENE_BODY_PATH = ROOT_DIR / "py_directinput_ffb" / "generated_scene_body.py"

PROMPT = textwrap.dedent(
    '''\
    turn this picture into a 10-second force feedback scene for a steering wheel.

    the main goal is to move the wheel, not leave it standing in one place and vibrating.
    use fx.constant(...) as the main effect for almost the entire scene. the wheel should
    spend most of the 10 seconds being pulled somewhere, sweeping between directions,
    leaning to one side, recoiling, drifting, or reacting to the person holding it.

    constant force is the animation. use changing positive and negative values to create
    actual directional movement. vary the shape of that movement: it can ramp, swing,
    pulse, hesitate, overshoot, snap back, change direction, or carry an uneven offset.
    don't use the same simple centered sine wave for every scene. choose the movement from
    the image and make the timing feel specific to it.

    fx.sine(...) is only extra texture. vibration is not a substitute for movement. keep
    it lower than the constant force most of the time, switch it off when it adds nothing,
    and never make a long section where the wheel only vibrates while constant force is
    zero. spring and damper can add shape, weight, or resistance, but keep them low enough
    that the wheel can still move. don't let them pin the wheel to the center.

    use state.x and state.x_velocity only to make the directional pull react to the person.
    don't turn every branch into a strong centering formula like -state.x * force. the
    scene should pull the wheel through space instead of always returning it to zero.

    build one continuous movement across the full 10 seconds. use as many time sections as
    the image needs, with uneven lengths. don't default to four equal parts or boundaries
    at 0, 2.5, 5, and 7.5 seconds. keep force flowing through section boundaries unless a
    sudden break is intentional. make the end connect naturally back to the beginning.

    the first line of the answer must be one short python comment explaining which visible
    detail or feeling in the picture led to this movement. after that, return only python
    code with no other comments or explanation. the code will be used as the body of:

    def update_effects(state, fx):
        ...

    you can use:
    - state.t: seconds since start
    - state.dt: frame delta seconds
    - state.x: wheel position, -1..+1
    - state.x_velocity: wheel speed
    - math
    - clamp(value, low, high)
    - clamp_force(value, limit)

    these are the only effect calls you may use:
    - fx.constant(force)
      signed directional force, keep it within -8000..8000
    - fx.sine(magnitude, period_us=55000)
      vibration or texture, magnitude is 0..10000, period_us must be at least 5000
    - fx.spring(coefficient, saturation=6000, dead_band=250)
      centering spring, coefficient is 0..10000
    - fx.damper(coefficient, saturation=6000, dead_band=0)
      resistance, coefficient is 0..10000

    start with these lines:

    cycle_time = 10.0
    t = state.t % cycle_time

    use if/elif/else time sections. call constant, sine, spring, and damper in every branch
    so old values never remain active by accident. constant should be meaningfully nonzero
    through most of the cycle. a branch with fx.constant(0) should be brief and intentional,
    not a place to fill time with vibration.

    most constant force should be around 2500..5500. strong pulls can reach 5500..6000.
    values up to 8000 are allowed only for short hits. don't hold high force for a long
    branch. make it move, fade, alternate, or release.

    no markdown, extra comments, imports, functions, classes, lambdas, file access,
    network calls, subprocesses, or loops. keep the first argument positional and use
    keyword arguments after it. use fx.sine(400, period_us=55000), not fx.sine(400, 55000).
    use fx.sine(0) to turn vibration off.
    '''
)


def clean_model_output(output_text: str) -> str:
    output_text = output_text.strip()
    output_text = re.sub(r"^```(?:python)?\s*", "", output_text)
    output_text = re.sub(r"\s*```$", "", output_text)
    return output_text.strip()


def get_ffb(path: str | os.PathLike[str]) -> str:
    image_path = Path(path)
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is missing. Add it to .env first.")

    image_bytes = image_path.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"

    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model="gemini-3.1-flash-lite",
        input=[
            {"type": "text", "text": PROMPT},
            {
                "type": "image",
                "data": image_b64,
                "mime_type": mime_type,
            },
        ],
    )

    output_text = clean_model_output(interaction.output_text)
    OUTPUT_PATH.write_text(output_text, encoding="utf-8")
    SCENE_BODY_PATH.write_text(output_text, encoding="utf-8")

    print(output_text)
    print(f"\nWrote scene to {SCENE_BODY_PATH}")
    return output_text


if __name__ == "__main__":
    path = input("photo path?: ")
    get_ffb(path)
