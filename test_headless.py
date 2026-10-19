"""
Headless Test Suite for CK3 Coat of Arms Converter
Verifies algorithm correctness, Paradox syntax compliance, coordinate math, and meshing efficiency.
"""

import re
import sys
from PIL import Image, ImageDraw
from ck3_converter import CK3CoAConverter


def create_test_image(width: int = 256, height: int = 256) -> Image.Image:
    """Creates a synthetic test image with geometric shapes and transparency."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base shield shape in gold
    draw.rectangle([20, 20, width - 20, height - 20], fill=(218, 165, 32, 255))
    # Red cross
    cx, cy = width // 2, height // 2
    arm = 24
    draw.rectangle([cx - arm, 20, cx + arm, height - 20], fill=(178, 34, 34, 255))
    draw.rectangle([20, cy - arm, width - 20, cy + arm], fill=(178, 34, 34, 255))
    # Blue central diamond
    draw.polygon(
        [(cx, cy - 40), (cx + 40, cy), (cx, cy + 40), (cx - 40, cy)],
        fill=(25, 25, 112, 255),
    )
    # White circle in center
    draw.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], fill=(255, 255, 255, 255))

    return img


def verify_paradox_syntax(code: str) -> bool:
    """Verifies that the generated Paradox script adheres to CK3 syntax rules."""
    # 1. Balanced braces
    open_braces = code.count("{")
    close_braces = code.count("}")
    assert open_braces == close_braces, f"Brace mismatch: {open_braces} open vs {close_braces} close"

    # 2. Pattern check
    assert 'pattern = "pattern__solid_designer.dds"' in code or 'pattern="pattern__solid_designer.dds"' in code, \
        "Missing pattern__solid_designer.dds declaration"

    # 3. Base color check
    color_matches = re.findall(r"color1\s*=\s*rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}", code)
    assert len(color_matches) >= 1, "Missing color1 rgb declaration"
    for r, g, b in color_matches:
        ir, ig, ib = int(r), int(g), int(b)
        assert 0 <= ir <= 255 and 0 <= ig <= 255 and 0 <= ib <= 255, f"RGB values out of bounds: {r}, {g}, {b}"

    # 4. Check texture declaration
    assert 'texture = "ce_block_02.dds"' in code, "Missing ce_block_02.dds texture"

    # 5. Check instance positions and scales
    pos_matches = re.findall(r"position\s*=\s*\{\s*([0-9\.]+)\s+([0-9\.]+)\s*\}", code)
    scale_matches = re.findall(r"scale\s*=\s*\{\s*([0-9\.]+)\s+([0-9\.]+)\s*\}", code)

    assert len(pos_matches) == len(scale_matches), "Mismatch between position and scale entries"
    assert len(pos_matches) > 0, "No instances generated"

    for px, py in pos_matches:
        fpx, fpy = float(px), float(py)
        assert 0.0 <= fpx <= 1.0, f"Position X {fpx} out of [0, 1] range"
        assert 0.0 <= fpy <= 1.0, f"Position Y {fpy} out of [0, 1] range"

    for sx, sy in scale_matches:
        fsx, fsy = float(sx), float(sy)
        assert fsx > 0.0 and fsy > 0.0, f"Invalid non-positive scale: {fsx}, {fsy}"

    return True


def run_all_tests():
    print("==================================================")
    print("CK3 Coat of Arms Converter - Headless Verification")
    print("==================================================")

    test_img = create_test_image(256, 256)
    print(f"Created synthetic test image: {test_img.size}, mode: {test_img.mode}")

    # Test 1: Standard conversion 64x64, 24 colors
    print("\n--- Test 1: Standard 64x64, 24 Colors, MedianCut ---")
    conv1 = CK3CoAConverter(
        grid_width=64,
        grid_height=64,
        num_colors=24,
        scale_multiplier=1.14,
        quantize_method="MEDIANCUT",
    )
    res1 = conv1.convert(test_img)
    print(f"Total instances generated: {res1.total_instances}")
    print(f"Background pixels saved: {res1.background_pixels_saved}")
    print(f"Reduction vs naive pixels: {res1.reduction_percentage:.1f}%")
    verify_paradox_syntax(res1.ck3_code)
    print("Syntax verification: PASSED")
    assert res1.total_instances < 64 * 64, "Meshing should generate far fewer instances than total pixels"

    # Test 2: FastOctree quantization
    print("\n--- Test 2: 64x64 FastOctree Quantization ---")
    conv2 = CK3CoAConverter(
        grid_width=64,
        grid_height=64,
        num_colors=16,
        scale_multiplier=1.14,
        quantize_method="FASTOCTREE",
    )
    res2 = conv2.convert(test_img)
    print(f"Total instances generated: {res2.total_instances}")
    verify_paradox_syntax(res2.ck3_code)
    print("Syntax verification: PASSED")

    # Test 3: Low resolution 32x32
    print("\n--- Test 3: Low Resolution 32x32 ---")
    conv3 = CK3CoAConverter(grid_width=32, grid_height=32, num_colors=8)
    res3 = conv3.convert(test_img)
    print(f"Total instances: {res3.total_instances}")
    verify_paradox_syntax(res3.ck3_code)
    print("Syntax verification: PASSED")

    # Test 4: High resolution 100x100
    print("\n--- Test 4: High Resolution 100x100 ---")
    conv4 = CK3CoAConverter(grid_width=100, grid_height=100, num_colors=32)
    res4 = conv4.convert(test_img)
    print(f"Total instances: {res4.total_instances}")
    verify_paradox_syntax(res4.ck3_code)
    print("Syntax verification: PASSED")

    # Test 5: Fully opaque solid image
    print("\n--- Test 5: Solid Image Background Optimization ---")
    solid_img = Image.new("RGB", (64, 64), (100, 150, 200))
    # Draw a 10x10 box in the center
    for x in range(27, 37):
        for y in range(27, 37):
            solid_img.putpixel((x, y), (255, 0, 0))
    conv5 = CK3CoAConverter(grid_width=64, grid_height=64, num_colors=16)
    res5 = conv5.convert(solid_img)
    print(f"Background color: {res5.background_color}")
    print(f"Background pixels saved: {res5.background_pixels_saved} / {64*64}")
    print(f"Total instances: {res5.total_instances}")
    # The 10x10 red box should mesh into a single 10x10 rectangle!
    assert res5.total_instances == 1, f"Expected exactly 1 merged rectangle, got {res5.total_instances}"
    print(f"Greedy meshing merged 100 pixels into {res5.total_instances} rectangle: PASSED")
    verify_paradox_syntax(res5.ck3_code)

    # Print sample of generated Paradox script
    print("\n--- Sample Generated Paradox CK3 Script (Snippet) ---")
    code_lines = res5.ck3_code.splitlines()
    for line in code_lines[:25]:
        print(line)

    print("\n==================================================")
    print("ALL HEADLESS TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
