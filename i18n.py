"""
Internationalization (i18n) module for CK3 Coat of Arms Converter.
Supports English (en) and Simplified Chinese (zh).
"""

from typing import Dict, Any

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Window & Header
        "window_title": "Crusader Kings III - Coat of Arms (CoA) Converter",
        "app_title": "CK3 CoA Converter",
        "app_subtitle": "Convert any image to Crusader Kings 3 Heraldry DNA",
        "language_label": "Language / 语言:",
        
        # Section: Input Image
        "sec_input_image": "INPUT IMAGE",
        "btn_open_image": "📁 Open Image (PNG / JPG / WEBP)",
        "btn_sample_shield": "🛡️ Reset to Sample Shield",
        "image_loaded_default": "Default Heraldic Shield (Sample)",
        "image_info": "Loaded: {filename}\nSize: {width}x{height} px",
        "dialog_open_title": "Select Image to Convert to CK3 Coat of Arms",
        "dialog_open_error": "Failed to Open Image",
        "dialog_open_error_msg": "Could not load image:\n{error}",

        # Section: Conversion Parameters
        "sec_parameters": "CONVERSION PARAMETERS",
        "lbl_resolution": "Grid Resolution: {res} x {res}",
        "lbl_colors": "Max Colors: {colors}",
        "lbl_scale": "Block Scale Multiplier: {scale:.2f}x (Prevents Hairlines)",

        # Section: Algorithm & Styling
        "sec_algorithm": "ALGORITHM & STYLING",
        "lbl_quantize": "Quantization Algorithm:",
        "chk_dithering": "Enable Dithering (Floyd-Steinberg)",
        "lbl_bg_mode": "Background Optimization:",
        "bg_mode_auto": "Auto (Most Frequent Color)",
        "bg_mode_none": "None (Emblems Only)",
        "lbl_header_format": "Paradox CoA Header Format:",
        "chk_wireframes": "Show 2D Meshing Wireframes",

        # Section: Export & Clipboard
        "sec_export": "EXPORT & CLIPBOARD",
        "btn_copy_clipboard": "📋 Copy CK3 Code to Clipboard",
        "btn_save_txt": "💾 Save Code to .txt",
        "btn_save_png": "🖼️ Save Preview Image (.png)",
        "status_copied": "✓ CK3 Code copied to clipboard! (Paste in CK3 CoA Editor)",
        "status_saved_txt": "✓ Code saved to {filename}",
        "status_saved_png": "✓ Preview saved to {filename}",
        "dialog_save_txt_title": "Save CK3 Coat of Arms Script",
        "dialog_save_png_title": "Save Quantized Grid Preview Image",
        "dialog_save_error": "Save Error",
        "dialog_save_error_msg": "Could not write file:\n{error}",

        # Stats Banner
        "stat_grid": "Grid: {width}x{height}",
        "stat_colors": "Colors: {colors}",
        "stat_instances": "Instances: {instances:,}",
        "stat_reduction": "Meshing Reduction: {reduction:.1f}% (saved {saved:,} bg px)",
        "badge_safe": "✓ CK3 Safe ({instances:,} / 3,500 emblems)",
        "badge_warning": "⚠️ High Instances: {instances:,} (>3,500 limit). May degrade CK3 FPS!",

        # Previews
        "preview_original": "Original Input Image",
        "preview_ck3": "Quantized CK3 Grid Preview (In-Game Reconstruction)",

        # Tabs & Details
        "tab_script_code": "Paradox CK3 Script Code",
        "tab_details": "Emblem Instance Details",
        "summary_title": "=== Coat of Arms Generation Summary ===",
        "summary_resolution": "Grid Resolution: {width} x {height} ({pixels} total pixels)",
        "summary_bg": "Base Background Color: rgb {bg} (Covered {saved} pixels without emblems)",
        "summary_colors": "Active Colors: {colors}",
        "summary_instances": "Total Emblems Generated: {instances}",
        "summary_reduction": "Greedy Meshing Savings: {reduction:.1f}% reduction",
        "summary_groups_header": "=== Colored Emblem Groups Breakdown ===",
        "summary_color_item": "• Color rgb {rgb}: {count} rectangular instances",
        "summary_sample_instance": "   Sample Instance 1: pos=({pos_x:.4f}, {pos_y:.4f}), scale=({scale_x:.4f}, {scale_y:.4f})",
    },
    "zh": {
        # Window & Header
        "window_title": "王国风云3 (CK3) 纹章转换器 (Coat of Arms Converter)",
        "app_title": "CK3 纹章代码转换器",
        "app_subtitle": "将任意图片转换为王国风云3自订纹章剪贴板代码",
        "language_label": "语言 / Language:",
        
        # Section: Input Image
        "sec_input_image": "输入图片",
        "btn_open_image": "📁 打开图片 (PNG / JPG / WEBP)",
        "btn_sample_shield": "🛡️ 重置为示例盾徽",
        "image_loaded_default": "默认示例盾徽 (Sample)",
        "image_info": "已加载: {filename}\n尺寸: {width}x{height} 像素",
        "dialog_open_title": "选择要转换为 CK3 纹章的图片",
        "dialog_open_error": "打开图片失败",
        "dialog_open_error_msg": "无法加载图片文件:\n{error}",

        # Section: Conversion Parameters
        "sec_parameters": "转换参数设置",
        "lbl_resolution": "网格分辨率: {res} x {res}",
        "lbl_colors": "最大颜色数: {colors}",
        "lbl_scale": "图块缩放系数: {scale:.2f}x (防止微小拼缝)",

        # Section: Algorithm & Styling
        "sec_algorithm": "算法与样式设置",
        "lbl_quantize": "色彩量化算法:",
        "chk_dithering": "启用抖动算法 (Floyd-Steinberg)",
        "lbl_bg_mode": "背景优化策略:",
        "bg_mode_auto": "自动检测 (出现最频繁颜色)",
        "bg_mode_none": "不优化 (仅图层图元)",
        "lbl_header_format": "Paradox 纹章代码头格式:",
        "chk_wireframes": "显示 2D 网格合并线框",

        # Section: Export & Clipboard
        "sec_export": "导出与剪贴板",
        "btn_copy_clipboard": "📋 复制 CK3 代码到剪贴板",
        "btn_save_txt": "💾 保存代码为 .txt 文件",
        "btn_save_png": "🖼️ 保存预览图 (.png)",
        "status_copied": "✓ CK3 纹章代码已复制到剪贴板！(可直接在游戏内点击“从剪贴板粘贴”)",
        "status_saved_txt": "✓ 代码已保存至 {filename}",
        "status_saved_png": "✓ 预览图已保存至 {filename}",
        "dialog_save_txt_title": "保存 CK3 纹章脚本文件",
        "dialog_save_png_title": "保存量化网格预览图片",
        "dialog_save_error": "保存失败",
        "dialog_save_error_msg": "无法写入文件:\n{error}",

        # Stats Banner
        "stat_grid": "网格: {width}x{height}",
        "stat_colors": "颜色数: {colors}",
        "stat_instances": "图元数: {instances:,}",
        "stat_reduction": "网格合并削减率: {reduction:.1f}% (免绘制 {saved:,} 个背景像素)",
        "badge_safe": "✓ CK3 运行流畅 ({instances:,} / 3,500 图元)",
        "badge_warning": "⚠️ 图元数量偏高: {instances:,} (超过3500限制)，可能影响游戏流畅度！",

        # Previews
        "preview_original": "原始输入图片",
        "preview_ck3": "CK3 网格量化预览 (游戏内实际渲染重构)",

        # Tabs & Details
        "tab_script_code": "Paradox 纹章脚本代码",
        "tab_details": "图元实例统计明细",
        "summary_title": "=== 纹章生成数据统计 ===",
        "summary_resolution": "网格分辨率: {width} x {height} (共计 {pixels} 像素)",
        "summary_bg": "基础背景色: rgb {bg} (作为底色免去绘制 {saved} 个图元)",
        "summary_colors": "使用颜色数量: {colors}",
        "summary_instances": "生成图元总数量: {instances}",
        "summary_reduction": "2D 贪婪合并优化率: 减少 {reduction:.1f}% 图元",
        "summary_groups_header": "=== 各颜色图层分组明细 ===",
        "summary_color_item": "• 颜色 rgb {rgb}: 包含 {count} 个矩形图元实例",
        "summary_sample_instance": "   示例图元 1: 位置=({pos_x:.4f}, {pos_y:.4f}), 缩放=({scale_x:.4f}, {scale_y:.4f})",
    },
}


class I18nManager:
    """Manages active language and string retrieval."""

    def __init__(self, default_lang: str = "en"):
        self.current_lang = default_lang if default_lang in TRANSLATIONS else "en"

    def set_language(self, lang: str):
        if lang in TRANSLATIONS:
            self.current_lang = lang

    def get(self, key: str, **kwargs: Any) -> str:
        lang_dict = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])
        template = lang_dict.get(key, TRANSLATIONS["en"].get(key, key))
        if kwargs:
            try:
                return template.format(**kwargs)
            except Exception:
                return template
        return template


# Singleton instance
i18n = I18nManager("en")
