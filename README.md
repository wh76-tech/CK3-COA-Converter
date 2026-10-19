# Crusader Kings III (CK3) Coat of Arms (CoA) Converter

A standalone native desktop GUI application built in Python (`CustomTkinter` and `Pillow`) that converts any user-selected image (PNG, JPG, JPEG, WEBP, BMP) into a Crusader Kings 3 (CK3) Coat of Arms clipboard code string ready to paste directly into the in-game Ruler Designer or Dynasty/Title Coat of Arms editor.

---

## Features

- **Native Modern Desktop GUI**: Built with CustomTkinter for high-DPI crisp dark theme styling, responsive parameter sliders, and real-time interactive preview.
- **Bilingual Interface (English / 简体中文)**: Switch languages on the fly with a single click without needing to restart the app.
- **Side-by-Side Visual Preview**: Displays the original uploaded image next to the exact reconstructed quantized CK3 grid preview so you know what it looks like before pasting into the game.
- **2D Greedy Rectangular Meshing**:
  - Automatically merges contiguous horizontal and vertical regions of identical color into maximal rectangles.
  - Slashes the number of required `instance` blocks by **70% to 90%** compared to naive pixel-by-pixel rendering.
- **Background Color Optimization**:
  - Automatically identifies the single most frequent RGB color in the grid and sets it as the solid shield background (`pattern="pattern__solid_designer.dds"`).
  - Eliminates the need to draw emblems for the dominant color, saving thousands of instances.
- **Transparency Handling**:
  - Pixels with alpha below 128 are treated as background and excluded from emblem generation.
- **Paradox Syntax & Colored Emblem Grouping**:
  - All rectangle instances of each color are grouped under a single `colored_emblem` block using `texture="ce_block_02.dds"` and `color1=rgb { R G B }`.
- **Anti-Hairline Overlap Scaling**:
  - Includes a "Block Scale Multiplier" slider (default `1.14x`, range `1.00x` to `1.30x`) to compensate for `ce_block_02.dds` internal padding, preventing hairline gaps between adjacent rectangles.
- **Real-Time Performance Warning**:
  - Real-time stats display: Grid Resolution, Active Colors, and Total Emblem Instances.
  - Automatically warns with an amber/red banner if instance count exceeds **3,500** (where in-game CK3 frame rates can degrade).
- **Clipboard & Export**:
  - One-click "Copy CK3 Code to Clipboard" button.
  - "Save Code to .txt" button.
  - "Save Preview Image (.png)" button.
  - Optional "Show 2D Meshing Wireframes" toggle to visually inspect the merged rectangle boundaries.

---

## Mathematical Coordinate Mapping

CK3 Coat of Arms coordinates run from `(0.0, 0.0)` at top-left to `(1.0, 1.0)` at bottom-right, where `position` is the center point of the emblem:

$$pos\_x = \frac{x + \frac{w}{2.0}}{W}$$
$$pos\_y = \frac{y + \frac{h}{2.0}}{H}$$

Emblem scales with the padding multiplier ($M$):

$$scale\_x = \frac{w}{W} \times M$$
$$scale\_y = \frac{h}{H} \times M$$

---

## Installation & Running

### Requirements
- Python 3.10+
- Dependencies: `Pillow>=10.0.0`, `customtkinter>=6.0.0`

### Quick Start
1. Run the launcher script:
   ```cmd
   run.bat
   ```
   Or run directly with Python:
   ```bash
   python main.py
   ```

2. To run the automated headless verification tests:
   ```bash
   python test_headless.py
   ```

---

## How to Import into CK3

1. Open the **Coat of Arms Editor** in *Crusader Kings III* (either in the Ruler Designer or by clicking the edit icon on your Dynasty / Title).
2. In the Converter desktop app, open your image, adjust the sliders to your preference, and click **"Copy CK3 Code to Clipboard"**.
3. In CK3, click the **"Paste from Clipboard"** button at the bottom-right of the Coat of Arms editor window.
4. Your custom design will instantly render on the heraldic shield!
