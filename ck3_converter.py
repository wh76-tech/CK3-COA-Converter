"""
CK3 Coat of Arms Converter Core Module
Converts any image (PNG/JPG/WEBP) into a Crusader Kings 3 (CK3) Coat of Arms (CoA) clipboard code string.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from PIL import Image, ImageDraw
import collections


@dataclass
class EmblemInstance:
    x: int
    y: int
    w: int
    h: int
    pos_x: float
    pos_y: float
    scale_x: float
    scale_y: float


@dataclass
class ConversionResult:
    ck3_code: str
    width: int
    height: int
    total_colors: int
    total_instances: int
    background_color: Optional[Tuple[int, int, int]]
    background_pixels_saved: int
    color_instances: Dict[Tuple[int, int, int], List[EmblemInstance]]
    preview_image: Image.Image
    quantized_grid: List[List[Optional[Tuple[int, int, int]]]]
    reduction_percentage: float


class CK3CoAConverter:
    """
    Handles image processing, color quantization, greedy rectangular meshing,
    coordinate mapping, and Paradox CK3 Coat of Arms script generation.
    """

    def __init__(
        self,
        grid_width: int = 64,
        grid_height: int = 64,
        num_colors: int = 24,
        scale_multiplier: float = 1.14,
        quantize_method: str = "MEDIANCUT",
        enable_dithering: bool = False,
        header_type: str = "coa_title_custom",
        bg_mode: str = "auto",
        custom_bg_color: Tuple[int, int, int] = (0, 0, 0),
        alpha_threshold: int = 128,
        show_wireframes: bool = False,
    ):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.num_colors = num_colors
        self.scale_multiplier = scale_multiplier
        self.quantize_method = quantize_method
        self.enable_dithering = enable_dithering
        self.header_type = header_type
        self.bg_mode = bg_mode  # "auto", "custom", or "none"
        self.custom_bg_color = custom_bg_color
        self.alpha_threshold = alpha_threshold
        self.show_wireframes = show_wireframes

    def convert(self, source_image: Image.Image) -> ConversionResult:
        """
        Converts a PIL Image into a CK3 Coat of Arms result.
        """
        W = max(16, min(120, self.grid_width))
        H = max(16, min(120, self.grid_height))
        K = max(2, min(64, self.num_colors))
        mult = max(0.8, min(1.5, self.scale_multiplier))

        # 1. Resize source image to grid resolution (W, H)
        img_rgba = source_image.convert("RGBA").resize(
            (W, H), resample=Image.Resampling.LANCZOS
        )

        # 2. Extract alpha mask and opaque pixels
        alpha_data = list(img_rgba.getchannel("A").getdata())
        is_opaque = [a >= self.alpha_threshold for a in alpha_data]

        # 3. Color Quantization using Pillow
        # Create an RGB image for quantization.
        # Transparent pixels are composited onto a neutral background so they don't corrupt quantization.
        rgb_img = Image.new("RGB", (W, H), (0, 0, 0))
        rgb_img.paste(img_rgba, mask=img_rgba.getchannel("A"))

        q_method = (
            Image.Quantize.MEDIANCUT
            if self.quantize_method.upper() == "MEDIANCUT"
            else Image.Quantize.FASTOCTREE
        )
        dither_flag = (
            Image.Dither.FLOYDSTEINBERG
            if self.enable_dithering
            else Image.Dither.NONE
        )

        # Quantize RGB image to K colors
        quantized = rgb_img.quantize(colors=K, method=q_method, dither=dither_flag)
        palette = quantized.getpalette()  # [r0, g0, b0, r1, g1, b1, ...]
        q_pixels = list(quantized.getdata())

        # 4. Construct 2D grid of colors: grid[y][x] = (r, g, b) or None (transparent)
        grid: List[List[Optional[Tuple[int, int, int]]]] = [
            [None for _ in range(W)] for _ in range(H)
        ]
        color_counts: collections.Counter = collections.Counter()

        for idx, (opaque, pal_idx) in enumerate(zip(is_opaque, q_pixels)):
            y = idx // W
            x = idx % W
            if opaque:
                base_idx = pal_idx * 3
                if base_idx + 2 < len(palette):
                    rgb = (palette[base_idx], palette[base_idx + 1], palette[base_idx + 2])
                else:
                    rgb = (0, 0, 0)
                grid[y][x] = rgb
                color_counts[rgb] += 1
            else:
                grid[y][x] = None

        # 5. Background Optimization
        # Find base background color
        bg_rgb: Optional[Tuple[int, int, int]] = None
        bg_pixels_saved = 0

        if self.bg_mode == "auto":
            if color_counts:
                # Most frequent opaque color
                bg_rgb = color_counts.most_common(1)[0][0]
                bg_pixels_saved = color_counts[bg_rgb]
            else:
                # Entire image is transparent
                bg_rgb = (0, 0, 0)
        elif self.bg_mode == "custom":
            bg_rgb = self.custom_bg_color
            bg_pixels_saved = color_counts.get(bg_rgb, 0)
        else:
            # "none"
            bg_rgb = (0, 0, 0)
            bg_pixels_saved = 0

        # Mark background pixels in grid as None so no emblem instances are generated for them
        working_grid: List[List[Optional[Tuple[int, int, int]]]] = [
            [None for _ in range(W)] for _ in range(H)
        ]
        unique_colors_used = set()

        for y in range(H):
            for x in range(W):
                c = grid[y][x]
                if c is not None and c != bg_rgb:
                    working_grid[y][x] = c
                    unique_colors_used.add(c)
                else:
                    working_grid[y][x] = None

        # 6. 2D Greedy Rectangular Meshing
        # We test both Horizontal-First and Vertical-First greedy meshing,
        # then select whichever generates fewer emblem instances!
        rects_h = self._greedy_meshing_horizontal(working_grid, W, H)
        rects_v = self._greedy_meshing_vertical(working_grid, W, H)
        rects = rects_h if len(rects_h) <= len(rects_v) else rects_v

        # 7. Coordinate & Scale Math
        # CK3 Coat of Arms coordinates: (0.0, 0.0) top-left, (1.0, 1.0) bottom-right
        # pos_x = (x + w / 2.0) / W
        # pos_y = (y + h / 2.0) / H
        # scale_x = (w / W) * scale_multiplier
        # scale_y = (h / H) * scale_multiplier
        color_instances: Dict[Tuple[int, int, int], List[EmblemInstance]] = collections.defaultdict(list)

        for c, x, y, w, h in rects:
            pos_x = (x + w / 2.0) / float(W)
            pos_y = (y + h / 2.0) / float(H)
            scale_x = (float(w) / float(W)) * mult
            scale_y = (float(h) / float(H)) * mult
            instance = EmblemInstance(
                x=x,
                y=y,
                w=w,
                h=h,
                pos_x=pos_x,
                pos_y=pos_y,
                scale_x=scale_x,
                scale_y=scale_y,
            )
            color_instances[c].append(instance)

        total_instances = sum(len(instances) for instances in color_instances.values())
        total_non_bg_pixels = sum(
            1 for row in working_grid for cell in row if cell is not None
        )
        reduction = (
            ((total_non_bg_pixels - total_instances) / max(1, total_non_bg_pixels)) * 100.0
            if total_non_bg_pixels > 0
            else 0.0
        )

        # 8. Generate CK3 Paradox Code
        ck3_code = self._generate_ck3_code(bg_rgb or (0, 0, 0), color_instances)

        # 9. Generate Reconstructed Preview Image
        preview_img = self._generate_preview_image(
            W, H, bg_rgb or (0, 0, 0), color_instances, mult, show_wireframes=self.show_wireframes
        )

        return ConversionResult(
            ck3_code=ck3_code,
            width=W,
            height=H,
            total_colors=len(color_counts),
            total_instances=total_instances,
            background_color=bg_rgb,
            background_pixels_saved=bg_pixels_saved,
            color_instances=color_instances,
            preview_image=preview_img,
            quantized_grid=grid,
            reduction_percentage=reduction,
        )

    def _greedy_meshing_horizontal(
        self, grid: List[List[Optional[Tuple[int, int, int]]]], W: int, H: int
    ) -> List[Tuple[Tuple[int, int, int], int, int, int, int]]:
        """
        Greedy rectangular meshing scanning horizontal lines first, then expanding vertically.
        Returns list of (color, x, y, w, h).
        """
        visited = [[False] * W for _ in range(H)]
        rectangles = []

        for y in range(H):
            for x in range(W):
                c = grid[y][x]
                if c is None or visited[y][x]:
                    continue

                # Expand horizontally as far as possible
                w = 1
                while x + w < W and not visited[y][x + w] and grid[y][x + w] == c:
                    w += 1

                # Expand vertically row by row matching width w
                h = 1
                while y + h < H:
                    can_expand = True
                    for col in range(x, x + w):
                        if visited[y + h][col] or grid[y + h][col] != c:
                            can_expand = False
                            break
                    if can_expand:
                        h += 1
                    else:
                        break

                # Mark covered cells
                for r in range(y, y + h):
                    for col in range(x, x + w):
                        visited[r][col] = True

                rectangles.append((c, x, y, w, h))

        return rectangles

    def _greedy_meshing_vertical(
        self, grid: List[List[Optional[Tuple[int, int, int]]]], W: int, H: int
    ) -> List[Tuple[Tuple[int, int, int], int, int, int, int]]:
        """
        Greedy rectangular meshing scanning vertical lines first, then expanding horizontally.
        Returns list of (color, x, y, w, h).
        """
        visited = [[False] * W for _ in range(H)]
        rectangles = []

        for x in range(W):
            for y in range(H):
                c = grid[y][x]
                if c is None or visited[y][x]:
                    continue

                # Expand vertically as far as possible
                h = 1
                while y + h < H and not visited[y + h][x] and grid[y + h][x] == c:
                    h += 1

                # Expand horizontally column by column matching height h
                w = 1
                while x + w < W:
                    can_expand = True
                    for row in range(y, y + h):
                        if visited[row][x + w] or grid[row][x + w] != c:
                            can_expand = False
                            break
                    if can_expand:
                        w += 1
                    else:
                        break

                # Mark covered cells
                for col in range(x, x + w):
                    for r in range(y, y + h):
                        visited[r][col] = True

                rectangles.append((c, x, y, w, h))

        return rectangles

    def _generate_ck3_code(
        self,
        bg_rgb: Tuple[int, int, int],
        color_instances: Dict[Tuple[int, int, int], List[EmblemInstance]],
    ) -> str:
        """
        Generates valid Paradox CK3 Coat of Arms script code.
        """
        lines = []
        header = self.header_type.strip()
        is_raw = header.lower() == "raw"

        if not is_raw:
            lines.append(f"{header} = {{")
            indent = "\t"
        else:
            indent = ""

        # Background solid pattern definition
        lines.append(f'{indent}pattern = "pattern__solid_designer.dds"')
        lines.append(f"{indent}color1 = rgb {{ {bg_rgb[0]} {bg_rgb[1]} {bg_rgb[2]} }}")
        lines.append(f"{indent}color2 = rgb {{ {bg_rgb[0]} {bg_rgb[1]} {bg_rgb[2]} }}")

        # Emblems grouped by color
        # Sort colors deterministically by instance count descending (render larger batches first)
        sorted_colors = sorted(
            color_instances.keys(),
            key=lambda c: len(color_instances[c]),
            reverse=True,
        )

        for rgb in sorted_colors:
            instances = color_instances[rgb]
            if not instances:
                continue

            lines.append(f"{indent}colored_emblem = {{")
            lines.append(f'{indent}\tcolor1 = rgb {{ {rgb[0]} {rgb[1]} {rgb[2]} }}')
            lines.append(f'{indent}\ttexture = "ce_block_02.dds"')

            for inst in instances:
                lines.append(f"{indent}\tinstance = {{")
                lines.append(
                    f"{indent}\t\tposition = {{ {inst.pos_x:.6f} {inst.pos_y:.6f} }}"
                )
                lines.append(
                    f"{indent}\t\tscale = {{ {inst.scale_x:.6f} {inst.scale_y:.6f} }}"
                )
                lines.append(f"{indent}\t}}")

            lines.append(f"{indent}}}")

        if not is_raw:
            lines.append("}")

        return "\n".join(lines)

    def _generate_preview_image(
        self,
        W: int,
        H: int,
        bg_rgb: Tuple[int, int, int],
        color_instances: Dict[Tuple[int, int, int], List[EmblemInstance]],
        mult: float,
        target_size: int = 512,
        show_wireframes: bool = False,
    ) -> Image.Image:
        """
        Reconstructs the quantized preview image from the generated rectangles and background color,
        scaling up crisply to target_size for display.
        """
        # Create base canvas at target size
        preview = Image.new("RGB", (target_size, target_size), bg_rgb)
        draw = ImageDraw.Draw(preview)

        # Scale factors to target_size
        sx = target_size / float(W)
        sy = target_size / float(H)

        for rgb, instances in color_instances.items():
            for inst in instances:
                x0 = inst.x * sx
                y0 = inst.y * sy
                x1 = (inst.x + inst.w) * sx
                y1 = (inst.y + inst.h) * sy

                if mult > 1.0:
                    center_x = (x0 + x1) / 2.0
                    center_y = (y0 + y1) / 2.0
                    half_w = ((x1 - x0) / 2.0) * mult
                    half_h = ((y1 - y0) / 2.0) * mult
                    rx0 = max(0.0, center_x - half_w)
                    ry0 = max(0.0, center_y - half_h)
                    rx1 = min(float(target_size), center_x + half_w)
                    ry1 = min(float(target_size), center_y + half_h)
                else:
                    rx0, ry0, rx1, ry1 = x0, y0, x1, y1

                draw.rectangle([rx0, ry0, rx1, ry1], fill=rgb)

                if show_wireframes:
                    # Draw a contrasting border for each merged rectangle
                    border_color = (255, 255, 255) if (rgb[0]*0.299 + rgb[1]*0.587 + rgb[2]*0.114) < 128 else (30, 30, 30)
                    draw.rectangle([x0, y0, x1, y1], outline=border_color, width=1)

        return preview

