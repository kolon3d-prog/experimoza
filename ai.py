from google import genai

path = input('photo path?:')
client = genai.Client()

with open(path, "rb") as f:
    image_bytes = f.read()
image_b64 = base64.b64encode(image_bytes).decode("utf_8")

interaction = client.interactions.create(
    model="gemini-3.1-flash-lite",
    input=[
        {"type": "text", "text": "You are a simracing expert..."},
        {
            "type": "image",
            "data": image_b64,
            "mime_type": "image/jpeg"
        }
    ]
)
print(interaction.output_text)
