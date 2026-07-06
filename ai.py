from google import genai
import base64
import os
from dotenv import load_dotenv

load_dotenv()

path = input('photo path?:')
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

with open(path, "rb") as f:
    image_bytes = f.read()
image_b64 = base64.b64encode(image_bytes).decode("utf_8")

interaction = client.interactions.create(
    model="gemini-3.1-flash-lite",
    input=[
        {"type": "text", "text": '''You are an elite Simracing and Force Feedback (FFB) tuning engineer, specializing in Moza Direct Drive wheelbases.
Your task is to analyze the provided image (which could be a screenshot from a racing simulator, a photo of a car, a racetrack, a type of terrain, or road surface) and generate the optimal force feedback and vibration configuration in JSON format.

---
### ANALYSIS PIPELINE

1. Identify the Vehicle Class:
   - Open-wheel / Formula: Needs low rotation angle (360-540), high responsiveness, low damper, high torque limit.
   - GT3 / Sportscar: Needs moderate rotation (540-900), balanced damping and friction.
   - Drift / Rally: Needs fast wheel return speed (limit_wheel_speed: 80-100), natural spring/inertia settings, and high rotation (900-1080).
   - Off-road / Trucks: Needs high rotation (900-1080), high damping (natural_damper) to avoid thumb injuries, and low wheel speed.

2. Identify the Surface / Terrain:
   - Smooth Asphalt (racetrack): Low equalizer settings for lower frequencies, moderate road_sensitivity (3-5).
   - Bumpy Asphalt / Street Track: High EqualizerAmp13 and EqualizerAmp22_5.
   - Gravel / Dirt / Sand: Maximum road_sensitivity (8-10), extremely high low-frequency equalizer values (EqualizerAmp7_5: 80-100, EqualizerAmp13: 70-90) to simulate heavy rocks and bumps.
   - Wet / Ice: Low overall ffb_strength, very low friction and damping to make the steering feel light and slippery.

---
### PARAMETER DICTIONARY & CONSTRAINTS

Your JSON response must match this schema exactly:

* wheelbase_basic_settings:
  - "limit_angle": integer [90 to 2000]. Steering rotation limit in degrees.
  - "game_ffb_strength": integer [0 to 100]. Overall force feedback gain.
  - "road_sensitivity": integer [0 to 10]. Road detail amplification.
  - "natural_damper": integer [0 to 100]. Steering wheel rotation resistance (viscosity).
  - "natural_friction": integer [0 to 100]. Static resistance when turning.
  - "limit_wheel_speed": integer [10 to 100]. Speed of self-centering rotation.
  - "peak_torque_limit": integer [50 to 100]. Max motor torque limit in %.

* road_vibrations_equalizer:
  - "EqualizerAmp7_5": integer [0 to 100]. Curbs, rumble strips, and heavy bumps.
  - "EqualizerAmp13": integer [0 to 100]. Road texture, gravel, small bumps.
  - "EqualizerAmp22_5": integer [0 to 100]. Medium bumps.
  - "EqualizerAmp39": integer [0 to 100]. Speed feeling, engine hum.
  - "EqualizerAmp55": integer [0 to 100]. Fine high-frequency vibrations.
  - "EqualizerAmp100": integer [0 to 100]. Micro-details of the road.

* directinput_effects:
  - "periodic_sine_vibration": Simulates constant engine vibrations (especially at idle).
    * "active": boolean.
    * "magnitude": integer [-10000 to 10000]. Strength of vibration.
    * "period_ms": integer [10 to 100]. Wave cycle time (frequency).
    * "phase": integer [0 to 36000]. Wave phase.
    * "offset": integer [-10000 to 10000].
  - "constant_shock_force": Simulates heavy impacts like hitting potholes or crash obstacles.
    * "active": boolean.
    * "magnitude": integer [-10000 to 10000]. Force of the shock impact.
  - "spring_return_force": Hardware-independent centering spring.
    * "active": boolean.
    * "offset": integer [-10000 to 10000]. Center offset.
    * "dead_band": integer [0 to 10000]. Zone around center with zero force.
    * "positive_coefficient": integer [0 to 10000]. Spring stiffness turning right.
    * "negative_coefficient": integer [0 to 10000]. Spring stiffness turning left.

---
### OUTPUT RULES
- Return ONLY valid JSON matching the format.
- Do NOT include any markdown blocks (like ```json ... ```) or explanatory text outside the JSON.
- Ensure all values are realistic based on the visual context of the image.
'''},
        {
            "type": "image",
            "data": image_b64,
            "mime_type": "image/jpeg"
        }
    ]
)
print(interaction.output_text)

with open("output.txt", "w") as f:
    f.write(interaction.output_text)