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
    Act as a poet, but for force feedback.
    Based on the picture, write Python code for a 10-second cyclic force-feedback "poem".
    The code should make the steering wheel feel like the image in a creative, physical way.
    Do not make a boring tuning preset. Make an active scene: the wheel may pull,
    kick, oscillate, resist, loosen, and change direction over time.

    Write only Python code that will be inserted as the body of:

    def update_effects(state, fx):
        ...

    Available variables:
    - state.t: seconds since start
    - state.dt: frame delta seconds
    - state.x: wheel position, -1..+1
    - state.x_velocity: wheel speed
    - math is available
    - clamp(value, low, high) is available
    - clamp_force(value, limit) is available

    Available effect calls:
    - fx.constant(force)
      Signed force. Negative pulls one way, positive pulls the other.
    - fx.sine(magnitude, period_us=45000)
      Vibration/texture. magnitude is 0..10000. period_us must be greater than 0.
    - fx.spring(coefficient, saturation=6000, dead_band=250)
      Hardware centering spring. coefficient is 0..10000.
    - fx.damper(coefficient, saturation=6000, dead_band=0)
      Hardware resistance/damping. coefficient is 0..10000.

    Format rules:
    - Output code only.
    - Do not use Markdown fences.
    - Do not include comments.
    - Do not include imports.
    - Do not define functions, classes, lambdas, files, network calls, subprocesses, or infinite loops.
    - Make the scene cyclic with: cycle_time = 10.0 and t = state.t % cycle_time.
    - Use if/elif/else time sections.
    - Always set all four effects in every branch: constant, sine, spring, damper.
    - Use keyword arguments after the first argument:
      good: fx.constant(force)
      bad:  fx.constant(value=force)
      good: fx.sine(400, period_us=45000)
      bad:  fx.sine(400, 45000)
    - To disable sine, write fx.sine(0), not fx.sine(0, 0).
    - Never use period_us below 5000.

    Safety/style rules:
    - Be expressive. Use the full -10000..10000 range when the image calls for drama.
    - Use fx.constant(...) as directional torque choreography:
      * positive and negative values should intentionally pull the wheel in different directions
      * use waves like math.sin(...) * 5000 for sweeping left-right motion
      * use short opposite-sign pulses for impacts, snaps, cracks, collisions, explosions, curbs, or rhythm
    - Normal motion can be 2500..6500.
    - Very intense pulls can be 6500..9000.
    - 9000..10000 is allowed for brief hits or violent moments, but do not hold it for a whole multi-second branch.
    - Avoid long static maximum force. If force is high, make it pulse, decay, alternate sign, or depend on state.x/state.x_velocity.
    - Do not over-center every branch. Some branches should be off-center, directional, or unstable when visually appropriate.
    - Use state.x and state.x_velocity to make the wheel fight back against the user, not just vibrate.
    - Good directional examples:
      fx.constant(math.sin(t * 5.0) * 4500)
      fx.constant(-state.x * 2500 + math.sin(t * 12.0) * 3500)
      fx.constant(7500 if t < 0.15 else -5500)
    - The result should feel alive and surprising, but not like a permanent full-force lock.
    '''
)


def clean_model_output(output_text: str) -> str:
    output_text = output_text.strip()
    output_text = re.sub(r"^```(?:python)?\s*", "", output_text)
    output_text = re.sub(r"\s*```$", "", output_text)
    return "\n".join(
        line for line in output_text.splitlines()
        if not line.lstrip().startswith("#")
    ).strip()


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
