"""
CK3 Coat of Arms (CoA) Converter - Desktop GUI Application
A native desktop application built with CustomTkinter and Pillow that converts any
image into a Crusader Kings 3 Coat of Arms clipboard code string.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, Tuple
from PIL import Image, ImageDraw

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from ck3_converter import CK3CoAConverter, ConversionResult


def create_default_heraldic_sample() -> Image.Image:
    """Creates a sample heraldic shield image to display on startup."""
    size = 400
    img = Image.new("RGBA", (size, size), (28, 30, 36, 255))
    draw = ImageDraw.Draw(img)

    # Shield outline shape
    # Shield field: Left half Azure, Right half Gules
    cx = size // 2
    draw.rectangle([40, 40, cx, size - 40], fill=(24, 76, 120, 255))
    draw.rectangle([cx, 40, size - 40, size - 40], fill=(168, 32, 40, 255))

    # Golden border
    draw.rectangle([40, 40, size - 40, size - 40], outline=(230, 180, 40, 255), width=8)

    # Golden chevron or cross
    cy = size // 2
    draw.rectangle([cx - 16, 40, cx + 16, size - 40], fill=(230, 180, 40, 255))
    draw.rectangle([40, cy - 16, size - 40, cy + 16], fill=(230, 180, 40, 255))

    # Center white diamond
    d = 45
    draw.polygon([(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)], fill=(245, 245, 245, 255))

    # Center emerald jewel
    j = 18
    draw.ellipse([cx - j, cy - j, cx + j, cy + j], fill=(34, 139, 34, 255))

    return img


class CK3CoAApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("Crusader Kings III - Coat of Arms (CoA) Converter")
        self.geometry("1340x880")
        self.minsize(1100, 750)

        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # State Variables
        self.source_image: Image.Image = create_default_heraldic_sample()
        self.source_filename: str = "Default Heraldic Shield (Sample)"
        self.current_result: Optional[ConversionResult] = None
        self._update_job = None

        # Build UI Components
        self._create_layout()
        self._trigger_conversion()

    def _create_layout(self):
        # Configure root grid weights: Sidebar (col 0, fixed/stretchable), Main view (col 1, expands)
        self.grid_columnconfigure(0, weight=0, minsize=380)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----------------------------------------------------
        # Left Sidebar (Parameters & Actions)
        # ----------------------------------------------------
        self.sidebar_frame = ctk.CTkScrollableFrame(self, width=380, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # App Title & Subtitle
        title_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="CK3 CoA Converter",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
        )
        title_label.pack(anchor="w", padx=20, pady=(15, 2))

        sub_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Convert any image to Crusader Kings 3 Heraldry DNA",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="gray70",
        )
        sub_label.pack(anchor="w", padx=20, pady=(0, 15))

        # --- Section: Image Input ---
        img_section = ctk.CTkFrame(self.sidebar_frame, fg_color=("gray85", "gray17"))
        img_section.pack(fill="x", padx=15, pady=8)

        img_header = ctk.CTkLabel(
            img_section,
            text="INPUT IMAGE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70"),
        )
        img_header.pack(anchor="w", padx=15, pady=(10, 5))

        self.btn_open = ctk.CTkButton(
            img_section,
            text="📁 Open Image (PNG / JPG / WEBP)",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            command=self._on_open_image,
        )
        self.btn_open.pack(fill="x", padx=15, pady=6)

        self.btn_sample = ctk.CTkButton(
            img_section,
            text="🛡️ Reset to Sample Shield",
            font=ctk.CTkFont(size=12),
            height=28,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            command=self._on_load_sample,
        )
        self.btn_sample.pack(fill="x", padx=15, pady=(0, 6))

        self.lbl_image_info = ctk.CTkLabel(
            img_section,
            text=f"Loaded: {self.source_filename}\nSize: {self.source_image.width}x{self.source_image.height} px",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            justify="left",
        )
        self.lbl_image_info.pack(anchor="w", padx=15, pady=(2, 10))

        # --- Section: Conversion Parameters ---
        param_section = ctk.CTkFrame(self.sidebar_frame, fg_color=("gray85", "gray17"))
        param_section.pack(fill="x", padx=15, pady=8)

        param_header = ctk.CTkLabel(
            param_section,
            text="CONVERSION PARAMETERS",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70"),
        )
        param_header.pack(anchor="w", padx=15, pady=(10, 5))

        # Slider 1: Grid Resolution (16 to 120, default 64)
        self.lbl_res = ctk.CTkLabel(
            param_section,
            text="Grid Resolution: 64 x 64",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_res.pack(anchor="w", padx=15, pady=(8, 2))

        self.slider_res = ctk.CTkSlider(
            param_section,
            from_=16,
            to=120,
            number_of_steps=104,
            command=self._on_slider_change,
        )
        self.slider_res.set(64)
        self.slider_res.pack(fill="x", padx=15, pady=(0, 5))

        # Slider 2: Colors K (2 to 64, default 24)
        self.lbl_colors = ctk.CTkLabel(
            param_section,
            text="Max Colors: 24",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_colors.pack(anchor="w", padx=15, pady=(8, 2))

        self.slider_colors = ctk.CTkSlider(
            param_section,
            from_=2,
            to=64,
            number_of_steps=62,
            command=self._on_slider_change,
        )
        self.slider_colors.set(24)
        self.slider_colors.pack(fill="x", padx=15, pady=(0, 5))

        # Slider 3: Block Scale Multiplier (1.00 to 1.30, default 1.14)
        self.lbl_scale = ctk.CTkLabel(
            param_section,
            text="Block Scale Multiplier: 1.14x (Prevents Hairlines)",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_scale.pack(anchor="w", padx=15, pady=(8, 2))

        self.slider_scale = ctk.CTkSlider(
            param_section,
            from_=1.00,
            to=1.30,
            number_of_steps=60,
            command=self._on_slider_change,
        )
        self.slider_scale.set(1.14)
        self.slider_scale.pack(fill="x", padx=15, pady=(0, 10))

        # --- Section: Advanced Algorithm Options ---
        adv_section = ctk.CTkFrame(self.sidebar_frame, fg_color=("gray85", "gray17"))
        adv_section.pack(fill="x", padx=15, pady=8)

        adv_header = ctk.CTkLabel(
            adv_section,
            text="ALGORITHM & STYLING",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70"),
        )
        adv_header.pack(anchor="w", padx=15, pady=(10, 5))

        # Quantization Method
        q_label = ctk.CTkLabel(adv_section, text="Quantization Algorithm:", font=ctk.CTkFont(size=12))
        q_label.pack(anchor="w", padx=15, pady=(4, 2))
        self.opt_quantize = ctk.CTkOptionMenu(
            adv_section,
            values=["MEDIANCUT", "FASTOCTREE"],
            command=lambda _: self._on_param_change(),
        )
        self.opt_quantize.set("MEDIANCUT")
        self.opt_quantize.pack(fill="x", padx=15, pady=(0, 8))

        # Dithering Checkbox
        self.chk_dither = ctk.CTkCheckBox(
            adv_section,
            text="Enable Dithering (Floyd-Steinberg)",
            font=ctk.CTkFont(size=12),
            command=self._on_param_change,
        )
        self.chk_dither.pack(anchor="w", padx=15, pady=(4, 8))

        # Background Mode
        bg_label = ctk.CTkLabel(adv_section, text="Background Optimization:", font=ctk.CTkFont(size=12))
        bg_label.pack(anchor="w", padx=15, pady=(4, 2))
        self.opt_bg = ctk.CTkOptionMenu(
            adv_section,
            values=["Auto (Most Frequent Color)", "None (Emblems Only)"],
            command=lambda _: self._on_param_change(),
        )
        self.opt_bg.set("Auto (Most Frequent Color)")
        self.opt_bg.pack(fill="x", padx=15, pady=(0, 8))

        # Header Syntax Format
        hdr_label = ctk.CTkLabel(adv_section, text="Paradox CoA Header Format:", font=ctk.CTkFont(size=12))
        hdr_label.pack(anchor="w", padx=15, pady=(4, 2))
        self.opt_header = ctk.CTkOptionMenu(
            adv_section,
            values=["coa_title_custom", "coa_rd_dynasty_custom", "coa_house_custom", "raw"],
            command=lambda _: self._on_param_change(),
        )
        self.opt_header.set("coa_title_custom")
        self.opt_header.pack(fill="x", padx=15, pady=(0, 8))

        # Show Wireframes Checkbox
        self.chk_wireframes = ctk.CTkCheckBox(
            adv_section,
            text="Show 2D Meshing Wireframes",
            font=ctk.CTkFont(size=12),
            command=self._on_param_change,
        )
        self.chk_wireframes.pack(anchor="w", padx=15, pady=(4, 12))

        # --- Section: Actions & Clipboard ---
        action_section = ctk.CTkFrame(self.sidebar_frame, fg_color=("gray85", "gray17"))
        action_section.pack(fill="x", padx=15, pady=(8, 20))

        action_header = ctk.CTkLabel(
            action_section,
            text="EXPORT & CLIPBOARD",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70"),
        )
        action_header.pack(anchor="w", padx=15, pady=(10, 5))

        self.btn_copy = ctk.CTkButton(
            action_section,
            text="📋 Copy CK3 Code to Clipboard",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#1f6aa5",
            hover_color="#144870",
            command=self._on_copy_clipboard,
        )
        self.btn_copy.pack(fill="x", padx=15, pady=6)

        self.btn_save_txt = ctk.CTkButton(
            action_section,
            text="💾 Save Code to .txt",
            font=ctk.CTkFont(size=13),
            height=34,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            command=self._on_save_txt,
        )
        self.btn_save_txt.pack(fill="x", padx=15, pady=(0, 6))

        self.btn_save_png = ctk.CTkButton(
            action_section,
            text="🖼️ Save Preview Image (.png)",
            font=ctk.CTkFont(size=12),
            height=30,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            command=self._on_save_png,
        )
        self.btn_save_png.pack(fill="x", padx=15, pady=(0, 10))

        self.lbl_action_status = ctk.CTkLabel(
            action_section,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2ecc71",
        )
        self.lbl_action_status.pack(anchor="center", padx=15, pady=(0, 10))

        # ----------------------------------------------------
        # Right Main Panel (Stats + Visual Preview + Code View)
        # ----------------------------------------------------
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_frame.grid_rowconfigure(1, weight=1)  # Preview row
        self.main_frame.grid_rowconfigure(2, weight=1)  # Code view row
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 1. Real-Time Stats Banner
        self.stats_frame = ctk.CTkFrame(self.main_frame, fg_color=("gray85", "gray17"), height=55)
        self.stats_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))

        self.lbl_stat_grid = ctk.CTkLabel(
            self.stats_frame,
            text="Grid: 64x64",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_stat_grid.pack(side="left", padx=(18, 12), pady=10)

        self.lbl_stat_colors = ctk.CTkLabel(
            self.stats_frame,
            text="Colors: 24",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_stat_colors.pack(side="left", padx=12, pady=10)

        self.lbl_stat_instances = ctk.CTkLabel(
            self.stats_frame,
            text="Instances: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_stat_instances.pack(side="left", padx=12, pady=10)

        self.lbl_stat_reduction = ctk.CTkLabel(
            self.stats_frame,
            text="Meshing Reduction: 0%",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
        )
        self.lbl_stat_reduction.pack(side="left", padx=12, pady=10)

        # Warning / Status Badge (Safe vs >3500 instances warning)
        self.lbl_warning_badge = ctk.CTkLabel(
            self.stats_frame,
            text="✓ CK3 Safe (< 3,500 emblems)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2ecc71",
        )
        self.lbl_warning_badge.pack(side="right", padx=(12, 18), pady=10)

        # 2. Side-by-Side Visual Previews
        self.preview_container = ctk.CTkFrame(self.main_frame, fg_color=("gray90", "gray14"))
        self.preview_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.preview_container.grid_columnconfigure(0, weight=1)
        self.preview_container.grid_columnconfigure(1, weight=1)
        self.preview_container.grid_rowconfigure(0, weight=1)

        # Left Canvas Frame: Original Image
        self.orig_box = ctk.CTkFrame(self.preview_container, fg_color=("gray85", "gray17"))
        self.orig_box.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.orig_title = ctk.CTkLabel(
            self.orig_box,
            text="Original Input Image",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.orig_title.pack(anchor="w", padx=15, pady=(10, 5))

        self.orig_canvas_label = ctk.CTkLabel(self.orig_box, text="")
        self.orig_canvas_label.pack(expand=True, padx=10, pady=(0, 10))

        # Right Canvas Frame: Quantized CK3 Preview
        self.ck3_box = ctk.CTkFrame(self.preview_container, fg_color=("gray85", "gray17"))
        self.ck3_box.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.ck3_title = ctk.CTkLabel(
            self.ck3_box,
            text="Quantized CK3 Grid Preview (In-Game Reconstruction)",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.ck3_title.pack(anchor="w", padx=15, pady=(10, 5))

        self.ck3_canvas_label = ctk.CTkLabel(self.ck3_box, text="")
        self.ck3_canvas_label.pack(expand=True, padx=10, pady=(0, 10))

        # 3. Code View Tabview / Textbox
        self.bottom_tabs = ctk.CTkTabview(self.main_frame, height=220)
        self.bottom_tabs.grid(row=2, column=0, sticky="nsew", padx=0, pady=(10, 0))

        self.tab_code = self.bottom_tabs.add("Paradox CK3 Script Code")
        self.tab_info = self.bottom_tabs.add("Emblem Instance Details")

        # Monospace Text Box for CK3 Code
        self.txt_code = ctk.CTkTextbox(
            self.tab_code,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none",
        )
        self.txt_code.pack(fill="both", expand=True, padx=5, pady=5)

        # Detail Info Textbox
        self.txt_info = ctk.CTkTextbox(
            self.tab_info,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none",
        )
        self.txt_info.pack(fill="both", expand=True, padx=5, pady=5)

    def _on_slider_change(self, _=None):
        # Update text labels
        res = int(self.slider_res.get())
        colors = int(self.slider_colors.get())
        scale = float(self.slider_scale.get())

        self.lbl_res.configure(text=f"Grid Resolution: {res} x {res}")
        self.lbl_colors.configure(text=f"Max Colors: {colors}")
        self.lbl_scale.configure(text=f"Block Scale Multiplier: {scale:.2f}x (Prevents Hairlines)")

        # Debounced trigger
        self._debounced_trigger()

    def _on_param_change(self):
        self._debounced_trigger()

    def _debounced_trigger(self):
        if self._update_job is not None:
            self.after_cancel(self._update_job)
        self._update_job = self.after(50, self._trigger_conversion)

    def _on_open_image(self):
        filetypes = [
            ("Supported Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
            ("PNG Images", "*.png"),
            ("JPEG Images", "*.jpg *.jpeg"),
            ("WebP Images", "*.webp"),
            ("All Files", "*.*"),
        ]
        filename = filedialog.askopenfilename(
            title="Select Image to Convert to CK3 Coat of Arms",
            filetypes=filetypes,
        )
        if not filename:
            return

        try:
            loaded_img = Image.open(filename)
            self.source_image = loaded_img.copy()
            self.source_filename = os.path.basename(filename)
            self.lbl_image_info.configure(
                text=f"Loaded: {self.source_filename}\nSize: {self.source_image.width}x{self.source_image.height} px"
            )
            self._trigger_conversion()
        except Exception as e:
            messagebox.showerror("Failed to Open Image", f"Could not load image:\n{e}")

    def _on_load_sample(self):
        self.source_image = create_default_heraldic_sample()
        self.source_filename = "Default Heraldic Shield (Sample)"
        self.lbl_image_info.configure(
            text=f"Loaded: {self.source_filename}\nSize: {self.source_image.width}x{self.source_image.height} px"
        )
        self._trigger_conversion()

    def _trigger_conversion(self):
        res = int(self.slider_res.get())
        colors = int(self.slider_colors.get())
        scale = float(self.slider_scale.get())
        q_method = self.opt_quantize.get()
        dither = bool(self.chk_dither.get())
        bg_mode_str = self.opt_bg.get()
        bg_mode = "auto" if "Auto" in bg_mode_str else "none"
        header = self.opt_header.get()
        show_wireframes = bool(self.chk_wireframes.get())

        converter = CK3CoAConverter(
            grid_width=res,
            grid_height=res,
            num_colors=colors,
            scale_multiplier=scale,
            quantize_method=q_method,
            enable_dithering=dither,
            header_type=header,
            bg_mode=bg_mode,
            show_wireframes=show_wireframes,
        )

        result = converter.convert(self.source_image)
        self.current_result = result
        self._update_ui_with_result(result)

    def _update_ui_with_result(self, res: ConversionResult):
        # 1. Update Stats Banner
        self.lbl_stat_grid.configure(text=f"Grid: {res.width}x{res.height}")
        self.lbl_stat_colors.configure(text=f"Colors: {res.total_colors}")
        self.lbl_stat_instances.configure(text=f"Instances: {res.total_instances:,}")
        self.lbl_stat_reduction.configure(
            text=f"Meshing Reduction: {res.reduction_percentage:.1f}% (saved {res.background_pixels_saved:,} bg px)"
        )

        # Warning threshold (> 3,500 instances)
        if res.total_instances > 3500:
            self.lbl_warning_badge.configure(
                text=f"⚠️ High Instances: {res.total_instances:,} (>3,500 limit). May degrade CK3 FPS!",
                text_color="#e74c3c",
            )
        else:
            self.lbl_warning_badge.configure(
                text=f"✓ CK3 Safe ({res.total_instances:,} / 3,500 emblems)",
                text_color="#2ecc71",
            )

        # 2. Update Previews
        # Original Image display (scaled to fit nicely in 320x320)
        disp_size = 320
        orig_copy = self.source_image.copy()
        orig_copy.thumbnail((disp_size, disp_size), Image.Resampling.LANCZOS)
        # Pad with transparent or dark canvas
        orig_padded = Image.new("RGBA", (disp_size, disp_size), (24, 26, 30, 255))
        ox = (disp_size - orig_copy.width) // 2
        oy = (disp_size - orig_copy.height) // 2
        if orig_copy.mode == "RGBA":
            orig_padded.paste(orig_copy, (ox, oy), mask=orig_copy)
        else:
            orig_padded.paste(orig_copy, (ox, oy))

        orig_ctk = ctk.CTkImage(
            light_image=orig_padded, dark_image=orig_padded, size=(disp_size, disp_size)
        )
        self.orig_canvas_label.configure(image=orig_ctk)
        self.orig_canvas_label.image = orig_ctk  # keep reference

        # CK3 Preview display
        preview_resized = res.preview_image.resize((disp_size, disp_size), Image.Resampling.NEAREST)
        ck3_ctk = ctk.CTkImage(
            light_image=preview_resized, dark_image=preview_resized, size=(disp_size, disp_size)
        )
        self.ck3_canvas_label.configure(image=ck3_ctk)
        self.ck3_canvas_label.image = ck3_ctk  # keep reference

        # 3. Update Code Textbox
        self.txt_code.delete("0.0", "end")
        self.txt_code.insert("0.0", res.ck3_code)

        # 4. Update Emblem Details Tab
        self.txt_info.delete("0.0", "end")
        info_lines = [
            f"=== Coat of Arms Generation Summary ===",
            f"Grid Resolution: {res.width} x {res.height} ({res.width * res.height} total pixels)",
            f"Base Background Color: rgb {res.background_color} (Covered {res.background_pixels_saved} pixels without emblems)",
            f"Active Colors: {len(res.color_instances)}",
            f"Total Emblems Generated: {res.total_instances}",
            f"Greedy Meshing Savings: {res.reduction_percentage:.1f}% reduction",
            "",
            "=== Colored Emblem Groups Breakdown ===",
        ]
        for rgb, instances in sorted(res.color_instances.items(), key=lambda item: len(item[1]), reverse=True):
            info_lines.append(f"• Color rgb {rgb}: {len(instances)} rectangular instances")
            if instances:
                first = instances[0]
                info_lines.append(
                    f"   Sample Instance 1: pos=({first.pos_x:.4f}, {first.pos_y:.4f}), scale=({first.scale_x:.4f}, {first.scale_y:.4f})"
                )

        self.txt_info.insert("0.0", "\n".join(info_lines))

    def _on_copy_clipboard(self):
        if not self.current_result:
            return
        self.clipboard_clear()
        self.clipboard_append(self.current_result.ck3_code)
        self.update()

        self.lbl_action_status.configure(
            text="✓ CK3 Code copied to clipboard! (Paste in CK3 CoA Editor)",
            text_color="#2ecc71",
        )
        self.after(4000, lambda: self.lbl_action_status.configure(text=""))

    def _on_save_txt(self):
        if not self.current_result:
            return
        filename = filedialog.asksaveasfilename(
            title="Save CK3 Coat of Arms Script",
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt"), ("Paradox Script", "*.txt *.gui *.ck3"), ("All Files", "*.*")],
            initialfile="ck3_coat_of_arms.txt",
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.current_result.ck3_code)
            self.lbl_action_status.configure(
                text=f"✓ Code saved to {os.path.basename(filename)}",
                text_color="#2ecc71",
            )
            self.after(4000, lambda: self.lbl_action_status.configure(text=""))
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not write file:\n{e}")

    def _on_save_png(self):
        if not self.current_result:
            return
        filename = filedialog.asksaveasfilename(
            title="Save Quantized Grid Preview Image",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            initialfile="ck3_preview.png",
        )
        if not filename:
            return
        try:
            self.current_result.preview_image.save(filename)
            self.lbl_action_status.configure(
                text=f"✓ Preview saved to {os.path.basename(filename)}",
                text_color="#2ecc71",
            )
            self.after(4000, lambda: self.lbl_action_status.configure(text=""))
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not write file:\n{e}")


def main():
    if ctk is None:
        print("Error: CustomTkinter is required. Please install it using: pip install customtkinter")
        sys.exit(1)

    app = CK3CoAApp()
    app.mainloop()


if __name__ == "__main__":
    main()
