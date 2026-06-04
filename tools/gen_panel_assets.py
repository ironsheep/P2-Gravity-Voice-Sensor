#!/usr/bin/env python3
"""
Generate the DEBUG PLOT control-panel artwork for demo_voice_recognizer.spin2.

Writes (into src/, next to the .spin2 so LAYER finds them by bare filename):
  panel_bg.bmp    - static background: title, CMD-ID + VOLUME readout boxes, 8 labeled buttons
  panel_font.bmp  - digit strip 0..9 + blank, green on black (the readout-box background)
  panel_hi.bmp    - strip of the 4 MODE buttons drawn SELECTED (active-mode highlight)

Both are 24-bit, uncompressed, no-alpha BMP (the only format DEBUG LAYER accepts).

The layout numbers below are the SINGLE SOURCE OF TRUTH: this script draws the art from
them AND prints a ready-to-paste Spin2 CON block of the same numbers, so the art and the
PLOT code can't drift. Re-run after any layout change and paste the printed CON values.
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "src")

# ---- window ----
W, H = 480, 320

# ---- colors ----
BG        = (28, 28, 34)
WHITE     = (235, 235, 235)
LABEL     = (150, 150, 160)
BOX_BG    = (0, 0, 0)
DIGIT_FG  = (40, 230, 90)        # green readout digits
MODE_BTN  = (60, 90, 130)        # mode buttons (blue), normal
MODE_HI   = (95, 150, 215)       # mode button when selected (brighter blue)
MODE_RING = (250, 225, 70)       # selected-button outline (amber/yellow)
ACT_BTN   = (110, 85, 45)        # bring-up buttons (amber)
BTN_TXT   = (240, 240, 240)

# ---- readout boxes (x, y, w, h) ----
# Box top sits at 58 so the 15px labels (drawn at y=38) clear the black box fill.
CMD_BOX = (20, 58, 210, 84)
VOL_BOX = (320, 58, 120, 84)

# ---- digit font cell ----
DIGIT_W, DIGIT_H = 38, 62
NUM_CELLS = 12                   # 0..9, blank (10), mute glyph (11)
BLANK_IDX = 10
MUTE_IDX  = 11
MUTE_SLASH = (230, 70, 70)       # red "off" slash across the speaker

CMD_DIGITS = 3                   # CMDID 0..208
VOL_DIGITS = 2

def slots(box, ndigits):
    bx, by, bw, bh = box
    total = ndigits * DIGIT_W
    x0 = bx + (bw - total) // 2
    y  = by + (bh - DIGIT_H) // 2
    return [x0 + i * DIGIT_W for i in range(ndigits)], y

CMD_SLOTS, CMD_Y = slots(CMD_BOX, CMD_DIGITS)
VOL_SLOTS, VOL_Y = slots(VOL_BOX, VOL_DIGITS)

# ---- buttons: (key, label, color) laid out in a 4-col grid, two rows ----
BTN_W, BTN_H = 105, 44
COLS_X = [15, 130, 245, 360]
ROW1_Y, ROW2_Y = 156, 222

# ---- recognized-phrase line (below the buttons) ----
# A static "HEARD" label is baked into the background at the left; the phrase to its right
# is drawn at runtime with the PLOT TEXT directive and erased by crop-blitting this clean
# background strip (which is plain BG to the right of the label) before each redraw.
PHRASE_DIV_Y = 272               # thin divider under the buttons
HEARD_Y      = 284               # baked "HEARD" label baseline (top-left)
PHRASE_X     = 90                # PLOT pen X where the phrase text starts
PHRASE_Y     = 284               # PLOT pen Y for the phrase text
PHRASE_TSIZE = 18                # PLOT TEXTSIZE for the phrase
PHRASE_CLR   = (86, 276, W - 90, 42)   # erase rect (x, y, w, h): right of the label, full width

BUTTONS = [
    ("SYNC",  "Sync",    COLS_X[0], ROW1_Y, MODE_BTN),
    ("SCAN",  "Scanner", COLS_X[1], ROW1_Y, MODE_BTN),
    ("POLL",  "Poller",  COLS_X[2], ROW1_Y, MODE_BTN),
    ("STOP",  "Stop",    COLS_X[3], ROW1_Y, MODE_BTN),
    ("WAKE",  "Wake",    COLS_X[0], ROW2_Y, ACT_BTN),
    ("VOLUP", "Vol +",   COLS_X[1], ROW2_Y, ACT_BTN),
    ("VOLDN", "Vol -",   COLS_X[2], ROW2_Y, ACT_BTN),
    ("MUTE",  "Mute",    COLS_X[3], ROW2_Y, ACT_BTN),
]

def load_font(size, bold=True):
    cands = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in cands:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def centered(draw, cx, cy, text, font, fill):
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (r - l) / 2 - l, cy - (b - t) / 2 - t), text, font=font, fill=fill)

def make_bg():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title = load_font(20)
    f_label = load_font(15)
    f_btn = load_font(20)

    d.text((15, 8), "DF2301Q Voice Recognizer  -  v0.1.0", font=f_title, fill=WHITE)
    d.line([(0, 36), (W, 36)], fill=(70, 70, 80), width=1)

    d.text((CMD_BOX[0], 38), "CMD ID", font=f_label, fill=LABEL)
    d.text((VOL_BOX[0], 38), "VOLUME", font=f_label, fill=LABEL)
    for box in (CMD_BOX, VOL_BOX):
        x, y, w, h = box
        d.rectangle([x, y, x + w, y + h], fill=BOX_BG, outline=(60, 60, 70))

    for _key, label, x, y, color in BUTTONS:
        d.rounded_rectangle([x, y, x + BTN_W, y + BTN_H], radius=8,
                            fill=color, outline=(20, 20, 24))
        centered(d, x + BTN_W / 2, y + BTN_H / 2, label, f_btn, BTN_TXT)

    d.line([(0, PHRASE_DIV_Y), (W, PHRASE_DIV_Y)], fill=(70, 70, 80), width=1)
    d.text((15, HEARD_Y), "HEARD", font=f_label, fill=LABEL)   # phrase is drawn at runtime to its right
    img.save(os.path.join(OUT_DIR, "panel_bg.bmp"))

def make_font():
    img = Image.new("RGB", (DIGIT_W * NUM_CELLS, DIGIT_H), BOX_BG)
    d = ImageDraw.Draw(img)
    f = load_font(52)
    for i in range(10):
        centered(d, i * DIGIT_W + DIGIT_W / 2, DIGIT_H / 2, str(i), f, DIGIT_FG)
    # cell 10 = blank (left black)
    # cell 11 = mute glyph: green speaker with a red "off" slash
    ox = MUTE_IDX * DIGIT_W
    d.rectangle([ox + 9, 26, ox + 15, 36], fill=DIGIT_FG)                       # speaker body
    d.polygon([(ox + 15, 26), (ox + 24, 17), (ox + 24, 45), (ox + 15, 36)], fill=DIGIT_FG)  # cone
    d.line([(ox + 6, 16), (ox + 30, 46)], fill=MUTE_SLASH, width=3)             # mute slash
    img.save(os.path.join(OUT_DIR, "panel_font.bmp"))

# mode buttons, in selected order -> highlight-strip cell index (matches demo's MODE_* mapping)
MODE_KEYS = ["SYNC", "SCAN", "POLL", "STOP"]

def make_hi():
    # Horizontal strip of the four MODE buttons drawn SELECTED. The demo crop-blits cell i
    # over the active button, and restores from the clean background (layer 1) to deselect.
    # Strip background is the panel BG so the rounded corners blend seamlessly when blitted.
    img = Image.new("RGB", (BTN_W * len(MODE_KEYS), BTN_H), BG)
    d = ImageDraw.Draw(img)
    f_btn = load_font(20)
    label_of = {key: label for key, label, *_ in BUTTONS}
    for i, key in enumerate(MODE_KEYS):
        x = i * BTN_W
        d.rounded_rectangle([x + 1, 1, x + BTN_W - 2, BTN_H - 2], radius=8,
                            fill=MODE_HI, outline=MODE_RING, width=3)
        centered(d, x + BTN_W / 2, BTN_H / 2, label_of[key], f_btn, BTN_TXT)
    img.save(os.path.join(OUT_DIR, "panel_hi.bmp"))

def emit_con():
    print("' ===== paste into demo_voice_recognizer.spin2 (generated by tools/gen_panel_assets.py) =====")
    print("CON")
    print(f"  WIN_W = {W}")
    print(f"  WIN_H = {H}")
    print(f"  DIGIT_W = {DIGIT_W}")
    print(f"  DIGIT_H = {DIGIT_H}")
    print(f"  BLANK_CELL = {BLANK_IDX}")
    print(f"  MUTE_CELL = {MUTE_IDX}")
    print(f"  BTN_W = {BTN_W}")
    print(f"  BTN_H = {BTN_H}")
    print(f"  CMD_Y = {CMD_Y}")
    print("  ' CMD-ID digit slot X (left..right)")
    for i, x in enumerate(CMD_SLOTS):
        print(f"  CMD_X{i} = {x}")
    print(f"  VOL_Y = {VOL_Y}")
    for i, x in enumerate(VOL_SLOTS):
        print(f"  VOL_X{i} = {x}")
    print("  ' recognized-phrase line (PLOT TEXT)")
    print(f"  PHRASE_X = {PHRASE_X}")
    print(f"  PHRASE_Y = {PHRASE_Y}")
    print(f"  PHRASE_TSIZE = {PHRASE_TSIZE}")
    print(f"  PHRASE_CLR_X = {PHRASE_CLR[0]}")
    print(f"  PHRASE_CLR_Y = {PHRASE_CLR[1]}")
    print(f"  PHRASE_CLR_W = {PHRASE_CLR[2]}")
    print(f"  PHRASE_CLR_H = {PHRASE_CLR[3]}")
    print("  ' button hit-zones: x1, y1, x2, y2")
    for key, _label, x, y, _c in BUTTONS:
        print(f"  BTN_{key}_X1 = {x}")
        print(f"  BTN_{key}_Y1 = {y}")
        print(f"  BTN_{key}_X2 = {x + BTN_W}")
        print(f"  BTN_{key}_Y2 = {y + BTN_H}")

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    make_bg()
    make_font()
    make_hi()
    emit_con()
    print("' wrote src/panel_bg.bmp, src/panel_font.bmp and src/panel_hi.bmp")
