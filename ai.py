import os
import base64
import mimetypes
import json
import requests
from dotenv import load_dotenv

# Load API key from environment variables
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

def encode_image(image_path):
    """Encodes a local image to base64 and determines the correct mime type."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at: {image_path}")
        
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"  # default fallback
        
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        
    return mime_type, encoded_string

def analyze_image(image_path, prompt, model="gemini-3.1-flash-lite"):
    """Sends a prompt and an image to the Google AI Studio API."""
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set in the .env file or environment.")

    # Encode the local image
    mime_type, base64_data = encode_image(image_path)

    # Construct the payload
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64_data
                    }
                }
            ]
        }]
    }

    headers = {
        "Content-Type": "application/json"
    }

    print(f"Sending request to Google AI Studio (Model: {model})...")
    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(payload)
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Request failed with status {response.status_code}: {response.text}")

if __name__ == "__main__":
    # Example usage:
    # 1. Replace 'test_image.jpg' with your actual image path
    # 2. Call the function
    try:
        image_path = "images.jpg"
        prompt = """
You are a simracing expert. Analyze the environment shown in the image and identify the road surface or obstacles (e.g., gravel, rumble strip, smooth tarmac, mud, or rain). 
Generate the corresponding physical steering wheel force feedback effects as a raw JSON array. 
Do not return any conversational text, code blocks, or markdown formatting outside the JSON array.
Strictly adhere to the following schema structure:
1. "constant" (use for continuous pulling forces or cornering weight):
   - "effect_type": "constant"
   - "level": integer between -32768 and 32767 (strength and direction)
   - "length": duration in milliseconds (or 4294967295 for infinite)
   - "direction": [1, 0, 0]
2. "periodic" (use for road vibrations, rumble strips, or engine vibration):
   - "effect_type": "periodic"
   - "wave_type": "sine", "triangle", "sawtooth_up", or "sawtooth_down"
   - "magnitude": integer between 0 and 32767 (vibration strength)
   - "period": integer (time in milliseconds for one wave cycle, e.g., 50)
   - "length": duration in milliseconds
   - "direction": [1, 0, 0]
3. "condition" (use for spring centering tension, dampening, natural friction, or inertia):
   - "effect_type": "condition"
   - "condition_type": "spring" (for self-centering/alignment torque), "damper" (for fluid resistance), "natural_friction" (for mechanical weight of steering rack/tires), or "inertia"
   - "right_coeff" and "left_coeff": integer between -32768 and 32767 (scaling factor of the resistance/centering force)
   - "deadband": integer (dead zone size)
   - "length": duration in milliseconds (or 4294967295 for infinite)
"""
        
        # Call the Google Gemini API with the image and FFB prompt
        result = analyze_image(image_path, prompt)
        
        print("\n--- Response ---")
        print(json.dumps(result, indent=2))
        with open("output.txt", "w") as file:
            file.write(result['candidates'][0]['content']['parts'][0]['text'])
        
    except FileNotFoundError:
        print("\nTo run this script, place a 'test_image.jpg' in this directory or update the image_path.")
    except Exception as e:
        print(f"\nError: {e}")
