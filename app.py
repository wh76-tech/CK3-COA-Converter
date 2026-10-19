"""
CK3 Coat of Arms (CoA) Converter - Desktop GUI Application
A native desktop application built with CustomTkinter and Pillow that converts any
image into a Crusader Kings 3 Coat of Arms clipboard code string.
Includes interactive visual crop/ROI frame and bilingual English / Simplified Chinese (简体中文) support.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageTk

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from ck3_converter import CK3CoAConverter, ConversionResult
from i18n import i18n


def create_default_heraldic_sample() -> Image.Image:
    """Creates a sample heraldic shield image to display on startup."""
    size = 400
    img = Image.new("RGBA", (size, size), (28, 30, 36, 255))
    draw = ImageDraw.Draw(img)

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

        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Window Configuration
        self.title(i18n.get("window_title"))
        self.geometry("1340x900")
        self.minsize(1100, 750)

        # State Variables
        self.source_image: Image.Image = create_default_heraldic_sample()
        self.source_filename: str = i18n.get("image_loaded_default")
        self.is_default_image: bool = True
        self.current_result: Optional[ConversionResult] = None
        self._update_job = None

        # Crop / ROI State
        self.crop_box: Tuple[int, int, int, int] = (0, 0, self.source_image.width, self.source_image.height)
        self.crop_drag_mode: str = "none"  # "none", "new", "move", "nw", "ne", "sw", "se"
        self.crop_drag_start = (0, 0)
        self.crop_box_start = (0, 0, 0, 0)
        self.crop_anchor = (0, 0)
        self.canvas_scale: float = 1.0
        self.canvas_offset_x: int = 0
        self.canvas_offset_y: int = 0
        self.orig_photo_img: Optional[ImageTk.PhotoImage] = None

        # Tab naming tracking
        self.tab_code_name = i18n.get("tab_script_code")
        self.tab_info_name = i18n.get("tab_details")

        # Build UI Components
        self._create_layout()
        self._render_original_preview()
        self._trigger_conversion()

    def _create_layout(self):
        # Configure root grid weights: Sidebar (col 0), Main view (col 1, expands)
        self.grid_columnconfigure(0, weight=0, minsize=380)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----------------------------------------------------
        # Left Sidebar (Parameters & Actions)
        # ----------------------------------------------------
        self.sidebar_frame = ctk.CTkScrollableFrame(self, width=380, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Language Selector Bar
        lang_bar = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        lang_bar.pack(fill="x", padx=20, pady=(12, 6))

        self.lbl_lang = ctk.CTkLabel(
            lang_bar,
            text=i18n.get("language_label"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray75",
        )
        self.lbl_lang.pack(side="left", padx=(0, 8))

        self.seg_lang = ctk.CTkSegmentedButton(
            lang_bar,
            values=["English", "简体中文"],
            command=self._on_language_change,
            height=28,
            font=ctk.CTkFont(size=12),
        )
        self.seg_lang.set("English" if i18n.current_lang == "en" else "简体中文")
        self.seg_lang.pack(side="right")

        # App Title & Subtitle
        self.title_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=i18n.get("app_title"),
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
        )
        self.title_label.pack(anchor="w", padx=20, pady=(4, 2))

        self.sub_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=i18n.get("app_subtitle"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="gray70",
        )
        self.sub_label.pack(anchor="w", padx=20, pady=(0, 10))

        # --- Section 1: Image Input ---
        self.img_section = ctk.CTkFrame(self.sidebar_frame, fg_color=("gray85", "gray17"))
        self.img_section.pack(fill="x", padx=15, pady=6)

        self.img_header = ctk.CTkLabel(
            self.img_section,
            text=i18n.get("sec_input_image"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70"),
        )
        self.img_header.pack(anchor="w", padx=15, pady=(8, 4))

        self.btn_open = ctk.CTkButton(
            self.img_section,
            text=i18n.get("btn_open_image"),
            font=ctk.CTkFont(size=13, weight="bold"),
            height=34,
            command=self._on_open_image,
        )
        self.btn_open.pack(fill="x", padx=15, pady=4)

        self.btn_sample = ctk.CTkButton(
            self.img_section,
            text=i18n.get("btn_sample_shield"),
            font=ctk.CTkFont(size=12),
            height=26,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            command=self._on_load_sample,
        )
        self.btn_sample.pack(fill="x", padx=15, pady=(0, 4))

        self.lbl_image_info = ctk.CTkLabel(
            self.img_section,
            text=i18n.get(
                "image_info",
                filename=self.source_filename,
                width=self.source_image.width,
                height=self.source_image.height,
            ),
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            justify="left",
        )
        self.lbl_image_info.pack(anchor="w", padx=15, pady=(2, 8))

        # --- Section 2: Crop & Selection Frame ---
        self.crop_section = ctk.CTkFrame(self.sidebar_frame, fg_color=("gray85", "gray17"))
        self.crop_section.pack(fill="x", padx=15, pady=6)

        self.crop_header = ctk.CTkLabel(
            self.crop_section,
            text=i18n.get("sec_crop"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70"),
        )
        self.crop_header.pack(anchor="w", padx=15, pady=(8, 4))

        # Checkbox: Convert Whole Picture
        self.chk_whole_pic = ctk.CTkCheckBox(
            self.crop_section,
            text=i18n.get("chk_whole_image"),
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_crop_whole_toggle,
        )
        self.chk_whole_pic.select()  # Default: Convert whole picture
        self.chk_whole_pic.pack(anchor="w", padx=15, pady=(4, 6))

        # Sub-frame for crop options (active when whole picture is unchecked)
        self.crop_options_frame = ctk.CTkFrame(self.crop_section, fg_color="transparent")
        self.crop_options_frame.pack(fill="x", padx=15, pady=(0, 6))

        self.lbl_crop_hint = ctk.CTkLabel(
            self.crop_options_frame,
            text=i18n.get("lbl_crop_hint"),
            font=ctk.CTkFont(size=11),
            text_color="#3b8ed0",
            wraplength=320,
            justify="left",
        )
        self.lbl_crop_hint.pack(anchor="w", pady=(2, 4))

        self.chk_square_crop = ctk.CTkCheckBox(
            self.crop_options_frame,
            text=i18n.get("chk_square_crop"),
            font=ctk.CTkFont(size=12),
            command=self._on_square_crop_toggle,
        )
        self.chk_square_crop.select()  # Default: 1:1 square crop
        self.chk_square_crop.pack(anchor="w", pady=(2, 4))

        self.btn_reset_crop = ctk.CTkButton(
            self.crop_options_frame,
            text=i18n.get("btn_reset_crop"),
            font=ctk.CTkFont(size=11),
            height=24,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            command=self._on_reset_crop_box,
        )
        self.btn_reset_crop.pack(fill="x", pady=(2, 4))

        self.lbl_crop_status = ctk.CTkLabel(
            self.crop_section,
            text=i18n.get("lbl_crop_full", width=self.source_image.width, height=self.source_image.height),
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            justify="left",
        )
        self.lbl_crop_status.pack(anchor="w", padx=15, pady=(0, 8))

        # --- Section 3: Conversion Parameters ---
        self.param_section = ctk.CTkFrame(self.sidebar_frame, fg_color=("gray85", "gray17"))
        self.param_section.pack(fill="x", padx=15, pady=6)

        self.param_header = ctk.CTkLabel(
            self.param_section,
            text=i18n.get("sec_parameters"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70"),
        )
        self.param_header.pack(anchor="w", padx=15, pady=(8, 4))

        # Slider 1: Grid Resolution (16 to 120, default 64)
        self.lbl_res = ctk.CTkLabel(
            self.param_section,
            text=i18n.get("lbl_resolution", res=64),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_res.pack(anchor="w", padx=15, pady=(6, 2))

        self.slider_res = ctk.CTkSlider(
            self.param_section,
            from_=16,
            to=120,
            number_of_steps=104,
            command=self._on_slider_change,
        )
        self.slider_res.set(64)
        self.slider_res.pack(fill="x", padx=15, pady=(0, 4))

        # Slider 2: Colors K (2 to 64, default 24)
        self.lbl_colors = ctk.CTkLabel(
            self.param_section,
            text=i18n.get("lbl_colors", colors=24),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_colors.pack(anchor="w", padx=15, pady=(6, 2))

        self.slider_colors = ctk.CTkSlider(
            self.param_section,
            from_=2,
            to=64,
            number_of_steps=62,
            command=self._on_slider_change,
        )
        self.slider_colors.set(24)
        self.slider_colors.pack(fill="x", padx=15, pady=(0, 4))

        # Slider 3: Block Scale Multiplier (1.00 to 1.30, default 1.14)
        self.lbl_scale = ctk.CTkLabel(
            self.param_section,
            text=i18n.get("lbl_scale", scale=1.14),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_scale.pack(anchor="w", padx=15, pady=(6, 2))

        self.slider_scale = ctk.CTkSlider(
            self.param_section,
            from_=1.00,
            to=1.30,
            number_of_steps=60,
            command=self._on_slider_change,
        )
        self.slider_scale.set(1.14)
        self.slider_scale.pack(fill="x", padx=15, pady=(0, 8))

        # --- Section 4: Advanced Algorithm Options ---
        self.adv_section = ctk.CTkFrame(self.sidebar_frame, fg_color=("gray85", "gray17"))
        self.adv_section.pack(fill="x", padx=15, pady=6)

        self.adv_header = ctk.CTkLabel(
            self.adv_section,
            text=i18n.get("sec_algorithm"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70"),
        )
        self.adv_header.pack(anchor="w", padx=15, pady=(8, 4))

        # Quantization Method
        self.q_label = ctk.CTkLabel(self.adv_section, text=i18n.get("lbl_quantize"), font=ctk.CTkFont(size=12))
        self.q_label.pack(anchor="w", padx=15, pady=(4, 2))
        self.opt_quantize = ctk.CTkOptionMenu(
            self.adv_section,
            values=["MEDIANCUT", "FASTOCTREE"],
            command=lambda _: self._on_param_change(),
        )
        self.opt_quantize.set("MEDIANCUT")
        self.opt_quantize.pack(fill="x", padx=15, pady=(0, 6))

        # Dithering Checkbox
        self.chk_dither = ctk.CTkCheckBox(
            self.adv_section,
            text=i18n.get("chk_dithering"),
            font=ctk.CTkFont(size=12),
            command=self._on_param_change,
        )
        self.chk_dither.pack(anchor="w", padx=15, pady=(4, 6))

        # Background Mode
        self.bg_label = ctk.CTkLabel(self.adv_section, text=i18n.get("lbl_bg_mode"), font=ctk.CTkFont(size=12))
        self.bg_label.pack(anchor="w", padx=15, pady=(4, 2))
        self.opt_bg = ctk.CTkOptionMenu(
            self.adv_section,
            values=[i18n.get("bg_mode_auto"), i18n.get("bg_mode_none")],
            command=lambda _: self._on_param_change(),
        )
        self.opt_bg.set(i18n.get("bg_mode_auto"))
        self.opt_bg.pack(fill="x", padx=15, pady=(0, 6))

        # Header Syntax Format
        self.hdr_label = ctk.CTkLabel(self.adv_section, text=i18n.get("lbl_header_format"), font=ctk.CTkFont(size=12))
        self.hdr_label.pack(anchor="w", padx=15, pady=(4, 2))
        self.opt_header = ctk.CTkOptionMenu(
            self.adv_section,
            values=["coa_title_custom", "coa_rd_dynasty_custom", "coa_house_custom", "raw"],
            command=lambda _: self._on_param_change(),
        )
        self.opt_header.set("coa_title_custom")
        self.opt_header.pack(fill="x", padx=15, pady=(0, 6))

        # Show Wireframes Checkbox
        self.chk_wireframes = ctk.CTkCheckBox(
            self.adv_section,
            text=i18n.get("chk_wireframes"),
            font=ctk.CTkFont(size=12),
            command=self._on_param_change,
        )
        self.chk_wireframes.pack(anchor="w", padx=15, pady=(4, 10))

        # --- Section 5: Actions & Clipboard ---
        self.action_section = ctk.CTkFrame(self.sidebar_frame, fg_color=("gray85", "gray17"))
        self.action_section.pack(fill="x", padx=15, pady=(6, 16))

        self.action_header = ctk.CTkLabel(
            self.action_section,
            text=i18n.get("sec_export"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70"),
        )
        self.action_header.pack(anchor="w", padx=15, pady=(8, 4))

        self.btn_copy = ctk.CTkButton(
            self.action_section,
            text=i18n.get("btn_copy_clipboard"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color="#1f6aa5",
            hover_color="#144870",
            command=self._on_copy_clipboard,
        )
        self.btn_copy.pack(fill="x", padx=15, pady=5)

        self.btn_save_txt = ctk.CTkButton(
            self.action_section,
            text=i18n.get("btn_save_txt"),
            font=ctk.CTkFont(size=13),
            height=32,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            command=self._on_save_txt,
        )
        self.btn_save_txt.pack(fill="x", padx=15, pady=(0, 5))

        self.btn_save_png = ctk.CTkButton(
            self.action_section,
            text=i18n.get("btn_save_png"),
            font=ctk.CTkFont(size=12),
            height=28,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            command=self._on_save_png,
        )
        self.btn_save_png.pack(fill="x", padx=15, pady=(0, 8))

        self.lbl_action_status = ctk.CTkLabel(
            self.action_section,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2ecc71",
        )
        self.lbl_action_status.pack(anchor="center", padx=15, pady=(0, 8))

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
            text=i18n.get("stat_grid", width=64, height=64),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_stat_grid.pack(side="left", padx=(18, 12), pady=10)

        self.lbl_stat_colors = ctk.CTkLabel(
            self.stats_frame,
            text=i18n.get("stat_colors", colors=24),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_stat_colors.pack(side="left", padx=12, pady=10)

        self.lbl_stat_instances = ctk.CTkLabel(
            self.stats_frame,
            text=i18n.get("stat_instances", instances=0),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_stat_instances.pack(side="left", padx=12, pady=10)

        self.lbl_stat_reduction = ctk.CTkLabel(
            self.stats_frame,
            text=i18n.get("stat_reduction", reduction=0.0, saved=0),
            font=ctk.CTkFont(size=12),
            text_color="gray70",
        )
        self.lbl_stat_reduction.pack(side="left", padx=12, pady=10)

        # Warning / Status Badge (Safe vs >3500 instances warning)
        self.lbl_warning_badge = ctk.CTkLabel(
            self.stats_frame,
            text=i18n.get("badge_safe", instances=0),
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

        # Left Canvas Frame: Original Image with Interactive Crop Box
        self.orig_box = ctk.CTkFrame(self.preview_container, fg_color=("gray85", "gray17"))
        self.orig_box.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.orig_title = ctk.CTkLabel(
            self.orig_box,
            text=i18n.get("preview_original"),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.orig_title.pack(anchor="w", padx=15, pady=(8, 4))

        # Tkinter Canvas for Interactive Crop Rendering and Mouse Events
        self.orig_canvas = tk.Canvas(
            self.orig_box,
            width=320,
            height=320,
            bg="#181a1e",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.orig_canvas.pack(expand=True, padx=10, pady=(0, 6))

        # Mouse Event Bindings for Cropping
        self.orig_canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.orig_canvas.bind("<B1-Motion>", self._on_canvas_motion)
        self.orig_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.orig_canvas.bind("<Motion>", self._on_canvas_hover)

        # Bottom badge on original frame
        self.orig_bottom_label = ctk.CTkLabel(
            self.orig_box,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
        )
        self.orig_bottom_label.pack(anchor="center", pady=(0, 6))

        # Right Canvas Frame: Quantized CK3 Preview
        self.ck3_box = ctk.CTkFrame(self.preview_container, fg_color=("gray85", "gray17"))
        self.ck3_box.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.ck3_title = ctk.CTkLabel(
            self.ck3_box,
            text=i18n.get("preview_ck3"),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.ck3_title.pack(anchor="w", padx=15, pady=(8, 4))

        self.ck3_canvas_label = ctk.CTkLabel(self.ck3_box, text="")
        self.ck3_canvas_label.pack(expand=True, padx=10, pady=(0, 6))

        self.ck3_bottom_label = ctk.CTkLabel(
            self.ck3_box,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
        )
        self.ck3_bottom_label.pack(anchor="center", pady=(0, 6))

        # 3. Code View Tabview / Textbox
        self.bottom_tabs = ctk.CTkTabview(self.main_frame, height=200)
        self.bottom_tabs.grid(row=2, column=0, sticky="nsew", padx=0, pady=(8, 0))

        self.tab_code = self.bottom_tabs.add(self.tab_code_name)
        self.tab_info = self.bottom_tabs.add(self.tab_info_name)

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

    # ----------------------------------------------------
    # Crop / Selection Handling & Canvas Rendering
    # ----------------------------------------------------
    def _canvas_to_img_coords(self, cx: int, cy: int) -> Tuple[int, int]:
        """Converts canvas pixel coordinates into source image coordinates."""
        orig_w = self.source_image.width
        orig_h = self.source_image.height
        if self.canvas_scale <= 0:
            return 0, 0
        img_x = int((cx - self.canvas_offset_x) / self.canvas_scale)
        img_y = int((cy - self.canvas_offset_y) / self.canvas_scale)
        img_x = max(0, min(orig_w, img_x))
        img_y = max(0, min(orig_h, img_y))
        return img_x, img_y

    def _img_to_canvas_coords(self, ix: int, iy: int) -> Tuple[int, int]:
        """Converts source image coordinates into canvas pixel coordinates."""
        cx = int(self.canvas_offset_x + ix * self.canvas_scale)
        cy = int(self.canvas_offset_y + iy * self.canvas_scale)
        return cx, cy

    def _render_original_preview(self):
        """Renders original image on canvas with optional interactive crop frame overlay."""
        disp_size = 320
        orig_w = self.source_image.width
        orig_h = self.source_image.height

        scale = min(disp_size / float(orig_w), disp_size / float(orig_h))
        disp_w = max(1, int(orig_w * scale))
        disp_h = max(1, int(orig_h * scale))
        offset_x = (disp_size - disp_w) // 2
        offset_y = (disp_size - disp_h) // 2

        self.canvas_scale = scale
        self.canvas_offset_x = offset_x
        self.canvas_offset_y = offset_y

        # Base image
        resized = self.source_image.copy()
        resized.thumbnail((disp_w, disp_h), Image.Resampling.LANCZOS)

        canvas_img = Image.new("RGBA", (disp_size, disp_size), (24, 26, 30, 255))
        if resized.mode == "RGBA":
            canvas_img.paste(resized, (offset_x, offset_y), mask=resized)
        else:
            canvas_img.paste(resized, (offset_x, offset_y))

        is_whole = bool(self.chk_whole_pic.get())

        if not is_whole:
            # Draw semi-transparent dimming outside the crop area and a bright border
            x1, y1, x2, y2 = self.crop_box
            cx1, cy1 = self._img_to_canvas_coords(x1, y1)
            cx2, cy2 = self._img_to_canvas_coords(x2, y2)
            rcx1, rcx2 = min(cx1, cx2), max(cx1, cx2)
            rcy1, rcy2 = min(cy1, cy2), max(cy1, cy2)

            # Darkened exterior overlay
            overlay = Image.new("RGBA", (disp_size, disp_size), (0, 0, 0, 155))
            odraw = ImageDraw.Draw(overlay)

            # Clear inside crop box so selected region is 100% bright
            odraw.rectangle([rcx1, rcy1, rcx2, rcy2], fill=(0, 0, 0, 0))

            # Draw glowing golden/cyan frame
            odraw.rectangle([rcx1, rcy1, rcx2, rcy2], outline=(255, 215, 0, 255), width=2)

            # Draw corner resize handles
            hs = 4
            for hx, hy in [(rcx1, rcy1), (rcx2, rcy1), (rcx1, rcy2), (rcx2, rcy2)]:
                odraw.rectangle([hx - hs, hy - hs, hx + hs, hy + hs], fill=(255, 215, 0, 255), outline=(0, 0, 0, 255))

            canvas_img = Image.alpha_composite(canvas_img, overlay)

            # Update crop status text
            bw = abs(x2 - x1)
            bh = abs(y2 - y1)
            self.lbl_crop_status.configure(
                text=i18n.get("lbl_crop_info", width=bw, height=bh, x=min(x1, x2), y=min(y1, y2)),
                text_color="#e6b800",
            )
            self.orig_bottom_label.configure(
                text=f"Selected: {bw}x{bh} px ({(bw*bh/(orig_w*orig_h))*100:.0f}% of image)"
            )
        else:
            # Whole picture is being used
            self.lbl_crop_status.configure(
                text=i18n.get("lbl_crop_full", width=orig_w, height=orig_h),
                text_color="gray70",
            )
            self.orig_bottom_label.configure(text=f"Full Image: {orig_w}x{orig_h} px")

        # Convert to ImageTk and update canvas
        self.orig_photo_img = ImageTk.PhotoImage(canvas_img)
        self.orig_canvas.delete("all")
        self.orig_canvas.create_image(0, 0, anchor="nw", image=self.orig_photo_img)

    def _on_canvas_press(self, event):
        """Handles mouse press on original image canvas."""
        if self.chk_whole_pic.get():
            # If user clicks and drags while whole picture is checked, uncheck it to enable cropping
            self.chk_whole_pic.deselect()
            self._on_crop_whole_toggle()

        orig_x, orig_y = self._canvas_to_img_coords(event.x, event.y)
        x1, y1, x2, y2 = self.crop_box
        cx1, cy1 = self._img_to_canvas_coords(x1, y1)
        cx2, cy2 = self._img_to_canvas_coords(x2, y2)
        rcx1, rcx2 = min(cx1, cx2), max(cx1, cx2)
        rcy1, rcy2 = min(cy1, cy2), max(cy1, cy2)

        tol = 10
        # Check corner handles
        if abs(event.x - rcx1) < tol and abs(event.y - rcy1) < tol:
            self.crop_drag_mode = "nw"
        elif abs(event.x - rcx2) < tol and abs(event.y - rcy1) < tol:
            self.crop_drag_mode = "ne"
        elif abs(event.x - rcx1) < tol and abs(event.y - rcy2) < tol:
            self.crop_drag_mode = "sw"
        elif abs(event.x - rcx2) < tol and abs(event.y - rcy2) < tol:
            self.crop_drag_mode = "se"
        elif min(x1, x2) <= orig_x <= max(x1, x2) and min(y1, y2) <= orig_y <= max(y1, y2):
            # Inside crop box -> move/pan mode
            self.crop_drag_mode = "move"
            self.crop_drag_start = (orig_x, orig_y)
            self.crop_box_start = (x1, y1, x2, y2)
        else:
            # Outside -> start new selection box
            self.crop_drag_mode = "new"
            self.crop_anchor = (orig_x, orig_y)
            self.crop_box = (orig_x, orig_y, orig_x, orig_y)

    def _on_canvas_motion(self, event):
        """Handles mouse drag to resize or move crop box."""
        if self.crop_drag_mode == "none":
            return

        curr_x, curr_y = self._canvas_to_img_coords(event.x, event.y)
        orig_w = self.source_image.width
        orig_h = self.source_image.height
        is_square = bool(self.chk_square_crop.get())

        if self.crop_drag_mode == "new":
            ax, ay = self.crop_anchor
            dx = curr_x - ax
            dy = curr_y - ay
            if is_square:
                side = max(abs(dx), abs(dy))
                sx = 1 if dx >= 0 else -1
                sy = 1 if dy >= 0 else -1
                curr_x = max(0, min(orig_w, ax + sx * side))
                curr_y = max(0, min(orig_h, ay + sy * side))
            self.crop_box = (min(ax, curr_x), min(ay, curr_y), max(ax, curr_x), max(ay, curr_y))

        elif self.crop_drag_mode == "move":
            start_x, start_y = self.crop_drag_start
            bx1, by1, bx2, by2 = self.crop_box_start
            dx = curr_x - start_x
            dy = curr_y - start_y
            bw = bx2 - bx1
            bh = by2 - by1
            nx1 = max(0, min(orig_w - bw, bx1 + dx))
            ny1 = max(0, min(orig_h - bh, by1 + dy))
            self.crop_box = (nx1, ny1, nx1 + bw, ny1 + bh)

        elif self.crop_drag_mode in ("nw", "ne", "sw", "se"):
            x1, y1, x2, y2 = self.crop_box
            if self.crop_drag_mode == "nw":
                x1, y1 = curr_x, curr_y
            elif self.crop_drag_mode == "ne":
                x2, y1 = curr_x, curr_y
            elif self.crop_drag_mode == "sw":
                x1, y2 = curr_x, curr_y
            elif self.crop_drag_mode == "se":
                x2, y2 = curr_x, curr_y

            if is_square:
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                side = max(w, h)
                if self.crop_drag_mode == "se":
                    x2 = min(orig_w, x1 + side)
                    y2 = min(orig_h, y1 + side)
                elif self.crop_drag_mode == "nw":
                    x1 = max(0, x2 - side)
                    y1 = max(0, y2 - side)
                elif self.crop_drag_mode == "ne":
                    x2 = min(orig_w, x1 + side)
                    y1 = max(0, y2 - side)
                elif self.crop_drag_mode == "sw":
                    x1 = max(0, x2 - side)
                    y2 = min(orig_h, y1 + side)

            self.crop_box = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

        self._render_original_preview()
        self._debounced_trigger()

    def _on_canvas_release(self, _event):
        """Finalizes crop box upon mouse release."""
        self.crop_drag_mode = "none"
        x1, y1, x2, y2 = self.crop_box
        # If user made a tiny/empty box, default to 75% center box
        if x2 - x1 < 8 or y2 - y1 < 8:
            orig_w, orig_h = self.source_image.width, self.source_image.height
            side = int(min(orig_w, orig_h) * 0.75)
            cx, cy = orig_w // 2, orig_h // 2
            self.crop_box = (
                max(0, cx - side // 2),
                max(0, cy - side // 2),
                min(orig_w, cx + side // 2),
                min(orig_h, cy + side // 2),
            )
        self._render_original_preview()
        self._trigger_conversion()

    def _on_canvas_hover(self, event):
        """Updates mouse cursor based on hover position."""
        if bool(self.chk_whole_pic.get()):
            self.orig_canvas.configure(cursor="crosshair")
            return

        x1, y1, x2, y2 = self.crop_box
        cx1, cy1 = self._img_to_canvas_coords(x1, y1)
        cx2, cy2 = self._img_to_canvas_coords(x2, y2)
        rcx1, rcx2 = min(cx1, cx2), max(cx1, cx2)
        rcy1, rcy2 = min(cy1, cy2), max(cy1, cy2)

        tol = 10
        if (abs(event.x - rcx1) < tol and abs(event.y - rcy1) < tol) or (abs(event.x - rcx2) < tol and abs(event.y - rcy2) < tol):
            self.orig_canvas.configure(cursor="size_nw_se")
        elif (abs(event.x - rcx2) < tol and abs(event.y - rcy1) < tol) or (abs(event.x - rcx1) < tol and abs(event.y - rcy2) < tol):
            self.orig_canvas.configure(cursor="size_ne_sw")
        elif rcx1 < event.x < rcx2 and rcy1 < event.y < rcy2:
            self.orig_canvas.configure(cursor="fleur")
        else:
            self.orig_canvas.configure(cursor="crosshair")

    def _on_crop_whole_toggle(self):
        """Toggles between whole picture conversion and cropped ROI conversion."""
        if not self.chk_whole_pic.get():
            # If turning off whole picture, initialize crop box to center square if not already set
            x1, y1, x2, y2 = self.crop_box
            orig_w, orig_h = self.source_image.width, self.source_image.height
            if x2 - x1 >= orig_w and y2 - y1 >= orig_h:
                side = int(min(orig_w, orig_h) * 0.75)
                cx, cy = orig_w // 2, orig_h // 2
                self.crop_box = (
                    max(0, cx - side // 2),
                    max(0, cy - side // 2),
                    min(orig_w, cx + side // 2),
                    min(orig_h, cy + side // 2),
                )
        self._render_original_preview()
        self._trigger_conversion()

    def _on_square_crop_toggle(self):
        """Enforces 1:1 square crop aspect ratio when checked."""
        if self.chk_square_crop.get() and not self.chk_whole_pic.get():
            x1, y1, x2, y2 = self.crop_box
            w = x2 - x1
            h = y2 - y1
            side = max(w, h)
            orig_w, orig_h = self.source_image.width, self.source_image.height
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            half = side // 2
            self.crop_box = (
                max(0, cx - half),
                max(0, cy - half),
                min(orig_w, cx + half),
                min(orig_h, cy + half),
            )
            self._render_original_preview()
            self._trigger_conversion()

    def _on_reset_crop_box(self):
        """Resets crop box to full image or center box."""
        orig_w, orig_h = self.source_image.width, self.source_image.height
        side = int(min(orig_w, orig_h) * 0.8)
        cx, cy = orig_w // 2, orig_h // 2
        self.crop_box = (
            max(0, cx - side // 2),
            max(0, cy - side // 2),
            min(orig_w, cx + side // 2),
            min(orig_h, cy + side // 2),
        )
        self._render_original_preview()
        self._trigger_conversion()

    # ----------------------------------------------------
    # UI Language & Param Handlers
    # ----------------------------------------------------
    def _on_language_change(self, selected_lang: str):
        new_lang = "zh" if "中文" in selected_lang else "en"
        i18n.set_language(new_lang)

        # Update window title
        self.title(i18n.get("window_title"))
        self.lbl_lang.configure(text=i18n.get("language_label"))
        self.title_label.configure(text=i18n.get("app_title"))
        self.sub_label.configure(text=i18n.get("app_subtitle"))

        # Section 1: Input image
        self.img_header.configure(text=i18n.get("sec_input_image"))
        self.btn_open.configure(text=i18n.get("btn_open_image"))
        self.btn_sample.configure(text=i18n.get("btn_sample_shield"))
        display_name = i18n.get("image_loaded_default") if self.is_default_image else self.source_filename
        self.lbl_image_info.configure(
            text=i18n.get(
                "image_info",
                filename=display_name,
                width=self.source_image.width,
                height=self.source_image.height,
            )
        )

        # Section 2: Crop
        self.crop_header.configure(text=i18n.get("sec_crop"))
        self.chk_whole_pic.configure(text=i18n.get("chk_whole_image"))
        self.lbl_crop_hint.configure(text=i18n.get("lbl_crop_hint"))
        self.chk_square_crop.configure(text=i18n.get("chk_square_crop"))
        self.btn_reset_crop.configure(text=i18n.get("btn_reset_crop"))

        # Section 3: Parameters
        self.param_header.configure(text=i18n.get("sec_parameters"))
        res = int(self.slider_res.get())
        colors = int(self.slider_colors.get())
        scale = float(self.slider_scale.get())
        self.lbl_res.configure(text=i18n.get("lbl_resolution", res=res))
        self.lbl_colors.configure(text=i18n.get("lbl_colors", colors=colors))
        self.lbl_scale.configure(text=i18n.get("lbl_scale", scale=scale))

        # Section 4: Algorithm
        self.adv_header.configure(text=i18n.get("sec_algorithm"))
        self.q_label.configure(text=i18n.get("lbl_quantize"))
        self.chk_dither.configure(text=i18n.get("chk_dithering"))
        self.bg_label.configure(text=i18n.get("lbl_bg_mode"))
        cur_bg_is_auto = "Auto" in self.opt_bg.get() or "自动" in self.opt_bg.get()
        self.opt_bg.configure(values=[i18n.get("bg_mode_auto"), i18n.get("bg_mode_none")])
        self.opt_bg.set(i18n.get("bg_mode_auto") if cur_bg_is_auto else i18n.get("bg_mode_none"))
        self.hdr_label.configure(text=i18n.get("lbl_header_format"))
        self.chk_wireframes.configure(text=i18n.get("chk_wireframes"))

        # Section 5: Export
        self.action_header.configure(text=i18n.get("sec_export"))
        self.btn_copy.configure(text=i18n.get("btn_copy_clipboard"))
        self.btn_save_txt.configure(text=i18n.get("btn_save_txt"))
        self.btn_save_png.configure(text=i18n.get("btn_save_png"))

        # Preview headers
        self.orig_title.configure(text=i18n.get("preview_original"))
        self.ck3_title.configure(text=i18n.get("preview_ck3"))

        # Rename tabs
        new_tab_code_name = i18n.get("tab_script_code")
        new_tab_info_name = i18n.get("tab_details")
        if new_tab_code_name != self.tab_code_name:
            self.bottom_tabs.rename(self.tab_code_name, new_tab_code_name)
            self.tab_code_name = new_tab_code_name
        if new_tab_info_name != self.tab_info_name:
            self.bottom_tabs.rename(self.tab_info_name, new_tab_info_name)
            self.tab_info_name = new_tab_info_name

        self._render_original_preview()
        if self.current_result:
            self._update_ui_with_result(self.current_result)

    def _on_slider_change(self, _=None):
        res = int(self.slider_res.get())
        colors = int(self.slider_colors.get())
        scale = float(self.slider_scale.get())

        self.lbl_res.configure(text=i18n.get("lbl_resolution", res=res))
        self.lbl_colors.configure(text=i18n.get("lbl_colors", colors=colors))
        self.lbl_scale.configure(text=i18n.get("lbl_scale", scale=scale))

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
            title=i18n.get("dialog_open_title"),
            filetypes=filetypes,
        )
        if not filename:
            return

        try:
            loaded_img = Image.open(filename)
            self.source_image = loaded_img.copy()
            self.source_filename = os.path.basename(filename)
            self.is_default_image = False
            self.crop_box = (0, 0, self.source_image.width, self.source_image.height)
            self.lbl_image_info.configure(
                text=i18n.get(
                    "image_info",
                    filename=self.source_filename,
                    width=self.source_image.width,
                    height=self.source_image.height,
                )
            )
            self._render_original_preview()
            self._trigger_conversion()
        except Exception as e:
            messagebox.showerror(
                i18n.get("dialog_open_error"),
                i18n.get("dialog_open_error_msg", error=str(e)),
            )

    def _on_load_sample(self):
        self.source_image = create_default_heraldic_sample()
        self.source_filename = i18n.get("image_loaded_default")
        self.is_default_image = True
        self.crop_box = (0, 0, self.source_image.width, self.source_image.height)
        self.lbl_image_info.configure(
            text=i18n.get(
                "image_info",
                filename=self.source_filename,
                width=self.source_image.width,
                height=self.source_image.height,
            )
        )
        self._render_original_preview()
        self._trigger_conversion()

    def _trigger_conversion(self):
        res = int(self.slider_res.get())
        colors = int(self.slider_colors.get())
        scale = float(self.slider_scale.get())
        q_method = self.opt_quantize.get()
        dither = bool(self.chk_dither.get())
        bg_mode_str = self.opt_bg.get()
        bg_mode = "auto" if ("Auto" in bg_mode_str or "自动" in bg_mode_str) else "none"
        header = self.opt_header.get()
        show_wireframes = bool(self.chk_wireframes.get())

        # Determine target image to convert (Full image vs Cropped region)
        if self.chk_whole_pic.get():
            img_to_convert = self.source_image
        else:
            x1, y1, x2, y2 = self.crop_box
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            if x2 - x1 >= 4 and y2 - y1 >= 4:
                img_to_convert = self.source_image.crop((x1, y1, x2, y2))
            else:
                img_to_convert = self.source_image

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

        result = converter.convert(img_to_convert)
        self.current_result = result
        self._update_ui_with_result(result)

    def _update_ui_with_result(self, res: ConversionResult):
        # 1. Update Stats Banner
        self.lbl_stat_grid.configure(text=i18n.get("stat_grid", width=res.width, height=res.height))
        self.lbl_stat_colors.configure(text=i18n.get("stat_colors", colors=res.total_colors))
        self.lbl_stat_instances.configure(text=i18n.get("stat_instances", instances=res.total_instances))
        self.lbl_stat_reduction.configure(
            text=i18n.get(
                "stat_reduction",
                reduction=res.reduction_percentage,
                saved=res.background_pixels_saved,
            )
        )

        # Warning threshold (> 3,500 instances)
        if res.total_instances > 3500:
            self.lbl_warning_badge.configure(
                text=i18n.get("badge_warning", instances=res.total_instances),
                text_color="#e74c3c",
            )
        else:
            self.lbl_warning_badge.configure(
                text=i18n.get("badge_safe", instances=res.total_instances),
                text_color="#2ecc71",
            )

        # 2. Update CK3 Preview Canvas
        disp_size = 320
        preview_resized = res.preview_image.resize((disp_size, disp_size), Image.Resampling.NEAREST)
        ck3_ctk = ctk.CTkImage(
            light_image=preview_resized, dark_image=preview_resized, size=(disp_size, disp_size)
        )
        self.ck3_canvas_label.configure(image=ck3_ctk)
        self.ck3_canvas_label.image = ck3_ctk
        self.ck3_bottom_label.configure(text=f"CK3 Shield Mesh: {res.width}x{res.height} ({res.total_instances:,} emblems)")

        # 3. Update Code Textbox
        self.txt_code.delete("0.0", "end")
        self.txt_code.insert("0.0", res.ck3_code)

        # 4. Update Emblem Details Tab
        self.txt_info.delete("0.0", "end")
        info_lines = [
            i18n.get("summary_title"),
            i18n.get("summary_resolution", width=res.width, height=res.height, pixels=res.width * res.height),
            i18n.get("summary_bg", bg=res.background_color, saved=res.background_pixels_saved),
            i18n.get("summary_colors", colors=len(res.color_instances)),
            i18n.get("summary_instances", instances=res.total_instances),
            i18n.get("summary_reduction", reduction=res.reduction_percentage),
            "",
            i18n.get("summary_groups_header"),
        ]
        for rgb, instances in sorted(res.color_instances.items(), key=lambda item: len(item[1]), reverse=True):
            info_lines.append(i18n.get("summary_color_item", rgb=rgb, count=len(instances)))
            if instances:
                first = instances[0]
                info_lines.append(
                    i18n.get(
                        "summary_sample_instance",
                        pos_x=first.pos_x,
                        pos_y=first.pos_y,
                        scale_x=first.scale_x,
                        scale_y=first.scale_y,
                    )
                )

        self.txt_info.insert("0.0", "\n".join(info_lines))

    def _on_copy_clipboard(self):
        if not self.current_result:
            return
        self.clipboard_clear()
        self.clipboard_append(self.current_result.ck3_code)
        self.update()

        self.lbl_action_status.configure(
            text=i18n.get("status_copied"),
            text_color="#2ecc71",
        )
        self.after(4000, lambda: self.lbl_action_status.configure(text=""))

    def _on_save_txt(self):
        if not self.current_result:
            return
        filename = filedialog.asksaveasfilename(
            title=i18n.get("dialog_save_txt_title"),
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
                text=i18n.get("status_saved_txt", filename=os.path.basename(filename)),
                text_color="#2ecc71",
            )
            self.after(4000, lambda: self.lbl_action_status.configure(text=""))
        except Exception as e:
            messagebox.showerror(
                i18n.get("dialog_save_error"),
                i18n.get("dialog_save_error_msg", error=str(e)),
            )

    def _on_save_png(self):
        if not self.current_result:
            return
        filename = filedialog.asksaveasfilename(
            title=i18n.get("dialog_save_png_title"),
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            initialfile="ck3_preview.png",
        )
        if not filename:
            return
        try:
            self.current_result.preview_image.save(filename)
            self.lbl_action_status.configure(
                text=i18n.get("status_saved_png", filename=os.path.basename(filename)),
                text_color="#2ecc71",
            )
            self.after(4000, lambda: self.lbl_action_status.configure(text=""))
        except Exception as e:
            messagebox.showerror(
                i18n.get("dialog_save_error"),
                i18n.get("dialog_save_error_msg", error=str(e)),
            )


def main():
    if ctk is None:
        print("Error: CustomTkinter is required. Please install it using: pip install customtkinter")
        sys.exit(1)

    app = CK3CoAApp()
    app.mainloop()


if __name__ == "__main__":
    main()
