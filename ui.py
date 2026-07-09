import customtkinter as ctk
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image
from tkinter import filedialog
from ai import get_ffb
from tkinterdnd2 import DND_FILES, TkinterDnD

ROOT_DIR = Path(__file__).resolve().parent
WHEEL_LAB_PATH = ROOT_DIR / "py_directinput_ffb" / "wheel_effect_lab.py"
STOP_REQUEST_PATH = ROOT_DIR / "py_directinput_ffb" / ".wheel_stop_request"
WHEEL_STATE_PATH = ROOT_DIR / "py_directinput_ffb" / "wheel_state.json"
SHIP_WHEEL_IMAGE_PATH = ROOT_DIR / "pngtree-ship-wheel-steer-a-boat-png-image_11569400.png"
WHEEL_VISUAL_MAX_DEGREES = 540
wheel_process = None
ship_wheel_base_image = None
current_ship_wheel_image = None
last_visual_degrees = None
BUTTON_FONT = (Manrope, 16, "bold")


def choose_image():
    global selected_image_path

    path = filedialog.askopenfilename(
        title="Choose image",
        filetypes=[
            ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
            ("All files", "*.*"),
        ],
    )

    if not path:
        return

    selected_image_path = path

    preview_image = ctk.CTkImage(
        light_image=Image.open(path),
        dark_image=Image.open(path),
        size=(300, 220),
    )

    image_label.configure(image=preview_image, text="")
    image_label.image = preview_image

    code=get_ffb(selected_image_path)
    print(code)

def on_file_drop(event):
    path = event.data.strip("{}")
    if not path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        print("not an image")
        return
    selected_image_path = path
    preview_image = ctk.CTkImage(
        light_image=Image.open(path),
        dark_image=Image.open(path),
        size=(300, 220),
    )

    image_label.configure(image=preview_image, text="")
    image_label.image = preview_image

    code=get_ffb(selected_image_path)
    print(code)


def start_wheel():
    global wheel_process

    if wheel_process is not None and wheel_process.poll() is None:
        print("wheel_effect_lab.py is already running")
        return

    clear_stop_request()
    wheel_process = subprocess.Popen(
        [sys.executable, str(WHEEL_LAB_PATH)],
        cwd=str(ROOT_DIR),
    )
    start_button.configure(state="disabled")
    stop_button.configure(state="normal")
    print("wheel started")


def stop_wheel():
    global wheel_process

    if wheel_process is None or wheel_process.poll() is not None:
        wheel_process = None
        start_button.configure(state="normal")
        stop_button.configure(state="disabled")
        print("wheel is not running")
        return

    request_wheel_stop()
    print("wheel stopping safely")
    app.after(1500, kill_wheel_if_needed)


def kill_wheel_if_needed():
    global wheel_process

    if wheel_process is not None and wheel_process.poll() is None:
        print("wheel did not stop cleanly, forcing process stop")
        wheel_process.terminate()
        try:
            wheel_process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            wheel_process.kill()
        print("wheel process force stopped")

    wheel_process = None
    start_button.configure(state="normal")
    stop_button.configure(state="disabled")


def request_wheel_stop():
    STOP_REQUEST_PATH.write_text("stop\n", encoding="utf-8")


def clear_stop_request():
    try:
        STOP_REQUEST_PATH.unlink()
    except FileNotFoundError:
        pass


def read_wheel_x():
    try:
        data = json.loads(WHEEL_STATE_PATH.read_text(encoding="utf-8"))
        return max(-1.0, min(1.0, float(data.get("x", 0.0))))
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return 0.0

def read_wheel_effects():
    try:
        data = json.loads(WHEEL_STATE_PATH.read_text(encoding="utf-8"))
        return {
            "constant": data.get("constant", 0),
            "sine": data.get("sine", 0),
            "spring": data.get("spring", 0),
            "damper": data.get("damper", 0),
        }
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return {"constant": 0, "sine": 0, "spring": 0, "damper": 0}


def update_ship_wheel_rotation():
    global current_ship_wheel_image, last_visual_degrees

    if ship_wheel_base_image is None:
        app.after(33, update_ship_wheel_rotation)
        return

    degrees = read_wheel_x() * WHEEL_VISUAL_MAX_DEGREES
    if last_visual_degrees is None or abs(degrees - last_visual_degrees) > 1:
        rotated_image = ship_wheel_base_image.rotate(
            -degrees,
            resample=Image.Resampling.BICUBIC,
        )
        current_ship_wheel_image = ctk.CTkImage(
            dark_image=rotated_image,
            size=(118, 118),
        )
        labelShipWheel.configure(image=current_ship_wheel_image)
        labelShipWheel.image = current_ship_wheel_image
        last_visual_degrees = degrees

    app.after(33, update_ship_wheel_rotation)


def on_close():
    global wheel_process

    if wheel_process is not None and wheel_process.poll() is None:
        request_wheel_stop()
        try:
            wheel_process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            wheel_process.terminate()
            try:
                wheel_process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                wheel_process.kill()

    wheel_process = None
    app.destroy()

class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

app = CTkDnD()
app.geometry("1100x700")
app.title("experimoza")
app.grid_columnconfigure(0, weight=1)  # main grows
app.grid_columnconfigure(1, weight=0)  # right panel fixed
app.grid_rowconfigure(0, weight=1)

main = ctk.CTkFrame(app)
main.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)

main.grid_rowconfigure(0, weight=0)
main.grid_rowconfigure(1, weight=1)
main.grid_rowconfigure(2, weight=0)
main.grid_columnconfigure(0, weight=1)

mainTop = ctk.CTkFrame(main)
mainTop.grid(row=0, column=0, sticky="nsew")

fileLabel = ctk.CTkLabel(mainTop, text="1. Source image", font=(BUTTON_FONT, 20))
fileLabel.pack(anchor="w", padx=12, pady=(12,0))


mainTopCard = ctk.CTkFrame(mainTop)
mainTopCard.pack(padx=12, pady=12, fill="both")
mainTopCard.drop_target_register(DND_FILES)
mainTopCard.dnd_bind("<<Drop>>", on_file_drop)

addImage = ctk.CTkImage( 
    dark_image=Image.open("187803-200.png"),
    size=(64, 64)
)

dropIcon=ctk.CTkLabel(mainTopCard, text="", image=addImage)
dropIcon.pack()

dropText=ctk.CTkLabel(mainTopCard, text="Drop image here", font=(BUTTON_FONT, 18))
dropText.pack()

dropText=ctk.CTkLabel(mainTopCard, text="or", font=(BUTTON_FONT, 16), text_color="#B8C1CC")
dropText.pack()

choose_button = ctk.CTkButton(
    mainTopCard,
    text="Choose image",
    font=BUTTON_FONT,
    command=choose_image,
)
choose_button.pack(padx=12, pady=12)

descrText=ctk.CTkLabel(mainTopCard, text="Experimoza turns it into a 10s force feedback scene", font=(BUTTON_FONT, 16), text_color="#B8C1CC")
descrText.pack(pady=(0, 12))

mainBottom = ctk.CTkFrame(main)
mainBottom.grid(row=2, column=0, sticky="nsew")
mainBottom.grid_rowconfigure(0, weight=1)
mainBottom.grid_columnconfigure(0, weight=1)
mainBottom.grid_columnconfigure(1, weight=1)

start_button = ctk.CTkButton(
    mainBottom,
    text="FEEL THE IMAGE",
    font=BUTTON_FONT,
    command=start_wheel,
)
start_button.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
stop_button = ctk.CTkButton(
    mainBottom,
    text="PANIC STOP :0",
    font=BUTTON_FONT,
    command=stop_wheel,
)
stop_button.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
stop_button.configure(state="disabled")

right_panel = ctk.CTkFrame(app, width=300)
right_panel.grid(row=0, column=1, sticky="ns", padx=12, pady=12)
right_panel.grid_propagate(False)

right_panel.grid_rowconfigure(0, weight=1)
right_panel.grid_rowconfigure(1, weight=1)
right_panel.grid_columnconfigure(0, weight=1)

right_top = ctk.CTkFrame(right_panel)
right_top.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
image_label = ctk.CTkLabel(right_top, text="No image selected", font=(BUTTON_FONT, 16), text_color="#B8C1CC")
image_label.pack(expand=True)

right_bottom = ctk.CTkFrame(right_panel)
right_bottom.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)

right_bottom.grid_rowconfigure(0, weight=1)
right_bottom.grid_columnconfigure(0, weight=1)

captain_stack = ctk.CTkFrame(right_bottom, fg_color="transparent")
captain_stack.grid(row=0, column=0)

pirate = ctk.CTkImage(dark_image=Image.open("Adobe Express - file.webp"), size=(128,128))
labelPirate = ctk.CTkLabel(master=captain_stack, text="", image=pirate)
labelPirate.grid(row=0, column=0, pady=(0, 6))

ship_wheel_base_image = Image.open(SHIP_WHEEL_IMAGE_PATH).convert("RGBA")
ship_wheel = ctk.CTkImage(
    dark_image=ship_wheel_base_image,
    size=(118, 118),
)
labelShipWheel = ctk.CTkLabel(master=captain_stack, text="", image=ship_wheel)
labelShipWheel.grid(row=1, column=0)

update_ship_wheel_rotation()
app.protocol("WM_DELETE_WINDOW", on_close)
app.mainloop()
