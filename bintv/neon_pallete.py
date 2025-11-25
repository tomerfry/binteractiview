#!/usr/bin/env python3
"""
Enhanced Neon Color Generator Module
A flexible module for generating neon color palettes for any number of elements
Perfect for terminal applications, data visualization, and UI theming
Now includes background-friendly color generation for terminal usage
"""

import colorsys
import math
import random
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum


class NeonTheme(Enum):
    """Predefined neon themes"""
    CYBER = "cyber"
    SYNTHWAVE = "synthwave"
    MIAMI = "miami"
    MATRIX = "matrix"
    VAPORWAVE = "vaporwave"
    ELECTRIC = "electric"
    PLASMA = "plasma"
    AURORA = "aurora"


class ColorMode(Enum):
    """Color generation modes"""
    FOREGROUND = "foreground"  # Bright colors for text/highlights
    BACKGROUND = "background"  # Darker colors suitable for backgrounds
    MUTED = "muted"           # Medium intensity for subtle accents
    GLOW = "glow"            # Soft glowing effect colors


@dataclass
class NeonColor:
    """Represents a neon color with metadata"""
    hex: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]
    name: Optional[str] = None
    brightness: float = 1.0
    mode: ColorMode = ColorMode.FOREGROUND
    
    def __str__(self):
        return self.hex
    
    def darken(self, factor: float = 0.8) -> 'NeonColor':
        """Return a darker version of this color"""
        h, s, l = self.hsl
        new_l = max(0.0, l * factor)
        r, g, b = colorsys.hls_to_rgb(h, new_l, s)
        return NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=ColorMode.BACKGROUND)
    
    def brighten(self, factor: float = 1.2) -> 'NeonColor':
        """Return a brighter version of this color"""
        h, s, l = self.hsl
        new_l = min(1.0, l * factor)
        r, g, b = colorsys.hls_to_rgb(h, new_l, s)
        return NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=ColorMode.FOREGROUND)
    
    def with_saturation(self, saturation: float) -> 'NeonColor':
        """Return a version with different saturation"""
        h, s, l = self.hsl
        r, g, b = colorsys.hls_to_rgb(h, l, saturation)
        return NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=self.mode)
    
    def to_background(self) -> 'NeonColor':
        """Convert to background-suitable version"""
        h, s, l = self.hsl
        # Reduce lightness for background use (10-25% range)
        new_l = max(0.1, min(0.25, l * 0.3))
        # Slightly reduce saturation for less eye strain
        new_s = max(0.4, s * 0.7)
        
        r, g, b = colorsys.hls_to_rgb(h, new_l, new_s)
        return NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=ColorMode.BACKGROUND)
    
    def to_muted(self) -> 'NeonColor':
        """Convert to muted version for subtle accents"""
        h, s, l = self.hsl
        # Medium lightness (30-50% range)
        new_l = max(0.3, min(0.5, l * 0.6))
        # Moderate saturation
        new_s = max(0.5, s * 0.8)
        
        r, g, b = colorsys.hls_to_rgb(h, new_l, new_s)
        return NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=ColorMode.MUTED)
    
    def to_glow(self) -> 'NeonColor':
        """Convert to soft glow version"""
        h, s, l = self.hsl
        # Soft lightness (35-60% range)
        new_l = max(0.35, min(0.6, l * 0.7))
        # Reduced saturation for soft effect
        new_s = max(0.3, s * 0.6)
        
        r, g, b = colorsys.hls_to_rgb(h, new_l, new_s)
        return NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=ColorMode.GLOW)
    
    def contrast_ratio(self, other: 'NeonColor') -> float:
        """Calculate contrast ratio between two colors (WCAG standard)"""
        def relative_luminance(rgb):
            r, g, b = [c/255.0 for c in rgb]
            r = r/12.92 if r <= 0.03928 else ((r + 0.055)/1.055) ** 2.4
            g = g/12.92 if g <= 0.03928 else ((g + 0.055)/1.055) ** 2.4
            b = b/12.92 if b <= 0.03928 else ((b + 0.055)/1.055) ** 2.4
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        l1 = relative_luminance(self.rgb)
        l2 = relative_luminance(other.rgb)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)
    
    def is_readable_on(self, background: 'NeonColor', aa_compliant: bool = True) -> bool:
        """Check if this color is readable on given background"""
        ratio = self.contrast_ratio(background)
        return ratio >= 4.5 if aa_compliant else ratio >= 3.0
    
    @classmethod
    def from_hex(cls, hex_color: str, name: str = None, mode: ColorMode = ColorMode.FOREGROUND) -> 'NeonColor':
        """Create NeonColor from hex string"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = [x/255.0 for x in rgb]
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return cls(
            hex=f"#{hex_color}",
            rgb=rgb,
            hsl=(h, s, l),
            name=name,
            brightness=l,
            mode=mode
        )
    
    @classmethod
    def from_rgb(cls, r: int, g: int, b: int, name: str = None, mode: ColorMode = ColorMode.FOREGROUND) -> 'NeonColor':
        """Create NeonColor from RGB values"""
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
        h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
        return cls(
            hex=hex_color,
            rgb=(r, g, b),
            hsl=(h, s, l),
            name=name,
            brightness=l,
            mode=mode
        )


class NeonPalette:
    """Container for a collection of neon colors"""
    
    def __init__(self, colors: List[NeonColor], name: str = "Custom", theme: Optional[NeonTheme] = None, mode: ColorMode = ColorMode.FOREGROUND):
        self.colors = colors
        self.name = name
        self.theme = theme
        self.mode = mode
    
    def __len__(self):
        return len(self.colors)
    
    def __getitem__(self, index):
        return self.colors[index]
    
    def __iter__(self):
        return iter(self.colors)
    
    def hex_colors(self) -> List[str]:
        """Get list of hex color strings"""
        return [color.hex for color in self.colors]
    
    def rgb_colors(self) -> List[Tuple[int, int, int]]:
        """Get list of RGB tuples"""
        return [color.rgb for color in self.colors]
    
    def to_background(self) -> 'NeonPalette':
        """Convert entire palette to background-suitable colors"""
        bg_colors = [color.to_background() for color in self.colors]
        return NeonPalette(bg_colors, f"{self.name} (Background)", self.theme, ColorMode.BACKGROUND)
    
    def to_muted(self) -> 'NeonPalette':
        """Convert entire palette to muted colors"""
        muted_colors = [color.to_muted() for color in self.colors]
        return NeonPalette(muted_colors, f"{self.name} (Muted)", self.theme, ColorMode.MUTED)
    
    def to_glow(self) -> 'NeonPalette':
        """Convert entire palette to glow colors"""
        glow_colors = [color.to_glow() for color in self.colors]
        return NeonPalette(glow_colors, f"{self.name} (Glow)", self.theme, ColorMode.GLOW)
    
    def get_matching_foregrounds(self, background_color: NeonColor = None) -> List[NeonColor]:
        """Get foreground colors that are readable on the given background"""
        if background_color is None:
            # Use a default dark background
            background_color = NeonColor.from_hex("#1a1a1a")
        
        readable_colors = []
        for color in self.colors:
            if color.is_readable_on(background_color):
                readable_colors.append(color)
            else:
                # Brighten the color until it's readable
                bright_color = color
                for _ in range(5):  # Max 5 attempts
                    bright_color = bright_color.brighten(1.3)
                    if bright_color.is_readable_on(background_color):
                        readable_colors.append(bright_color)
                        break
                else:
                    # If still not readable, add anyway but warn
                    readable_colors.append(bright_color)
        
        return readable_colors
    
    def extend(self, count: int, method: str = 'interpolate') -> 'NeonPalette':
        """Extend palette to specified count using various methods"""
        if count <= len(self.colors):
            return NeonPalette(self.colors[:count], self.name, self.theme, self.mode)
        
        generator = NeonGenerator()
        if method == 'interpolate':
            new_colors = generator._interpolate_colors(self.colors, count)
        elif method == 'variations':
            new_colors = generator._create_variations(self.colors, count)
        elif method == 'harmony':
            new_colors = generator._extend_harmony(self.colors, count)
        else:
            new_colors = generator._interpolate_colors(self.colors, count)
        
        return NeonPalette(new_colors, self.name, self.theme, self.mode)


class NeonGenerator:
    """Main class for generating neon color palettes"""
    
    def __init__(self):
        self.themes = {
            NeonTheme.CYBER: {
                'name': 'Cyberpunk',
                'base_hues': [120, 300, 180, 15, 270, 60, 330, 150],  # Green, Magenta, Cyan, Orange, Purple, Yellow, Pink, Lime
                'saturation_range': {
                    ColorMode.FOREGROUND: (0.8, 1.0),
                    ColorMode.BACKGROUND: (0.4, 0.7),
                    ColorMode.MUTED: (0.5, 0.8),
                    ColorMode.GLOW: (0.3, 0.6)
                },
                'lightness_range': {
                    ColorMode.FOREGROUND: (0.5, 0.9),
                    ColorMode.BACKGROUND: (0.1, 0.25),
                    ColorMode.MUTED: (0.3, 0.5),
                    ColorMode.GLOW: (0.35, 0.6)
                },
                'accent_colors': ['#00ff41', '#ff0080', '#00ffff', '#ff4500']
            },
            NeonTheme.SYNTHWAVE: {
                'name': 'Synthwave',
                'base_hues': [320, 260, 210, 170, 50, 20, 340, 280],  # Pink, Purple, Blue, Mint, Yellow, Orange, Magenta, Violet
                'saturation_range': {
                    ColorMode.FOREGROUND: (0.85, 1.0),
                    ColorMode.BACKGROUND: (0.5, 0.75),
                    ColorMode.MUTED: (0.6, 0.85),
                    ColorMode.GLOW: (0.4, 0.7)
                },
                'lightness_range': {
                    ColorMode.FOREGROUND: (0.4, 0.8),
                    ColorMode.BACKGROUND: (0.12, 0.28),
                    ColorMode.MUTED: (0.3, 0.5),
                    ColorMode.GLOW: (0.35, 0.6)
                },
                'accent_colors': ['#ff006e', '#8338ec', '#3a86ff', '#06ffa5']
            },
            NeonTheme.MIAMI: {
                'name': 'Miami Vice',
                'base_hues': [300, 180, 30, 270, 120, 330, 210, 45],  # Hot pink, Cyan, Orange, Orchid, Lime, Pink, Blue, Gold
                'saturation_range': {
                    ColorMode.FOREGROUND: (0.9, 1.0),
                    ColorMode.BACKGROUND: (0.5, 0.8),
                    ColorMode.MUTED: (0.6, 0.9),
                    ColorMode.GLOW: (0.4, 0.7)
                },
                'lightness_range': {
                    ColorMode.FOREGROUND: (0.5, 0.85),
                    ColorMode.BACKGROUND: (0.15, 0.3),
                    ColorMode.MUTED: (0.35, 0.55),
                    ColorMode.GLOW: (0.4, 0.65)
                },
                'accent_colors': ['#ff0080', '#00ffff', '#ff8c00', '#9932cc']
            },
            NeonTheme.MATRIX: {
                'name': 'Matrix',
                'base_hues': [120, 110, 100, 130, 90, 140, 105, 115],  # Various greens
                'saturation_range': {
                    ColorMode.FOREGROUND: (0.7, 1.0),
                    ColorMode.BACKGROUND: (0.4, 0.7),
                    ColorMode.MUTED: (0.5, 0.8),
                    ColorMode.GLOW: (0.3, 0.6)
                },
                'lightness_range': {
                    ColorMode.FOREGROUND: (0.4, 0.9),
                    ColorMode.BACKGROUND: (0.1, 0.22),
                    ColorMode.MUTED: (0.3, 0.5),
                    ColorMode.GLOW: (0.35, 0.6)
                },
                'accent_colors': ['#00ff41', '#39ff14', '#32cd32', '#7fff00']
            },
            NeonTheme.VAPORWAVE: {
                'name': 'Vaporwave',
                'base_hues': [300, 180, 320, 270, 30, 290, 200, 340],  # Magenta, Cyan, Pink, Purple, Orange, Orchid, Turquoise, Deep pink
                'saturation_range': {
                    ColorMode.FOREGROUND: (0.8, 1.0),
                    ColorMode.BACKGROUND: (0.45, 0.7),
                    ColorMode.MUTED: (0.6, 0.85),
                    ColorMode.GLOW: (0.35, 0.65)
                },
                'lightness_range': {
                    ColorMode.FOREGROUND: (0.45, 0.8),
                    ColorMode.BACKGROUND: (0.12, 0.25),
                    ColorMode.MUTED: (0.32, 0.52),
                    ColorMode.GLOW: (0.38, 0.62)
                },
                'accent_colors': ['#ff00ff', '#00ffff', '#ff69b4', '#9370db']
            },
            NeonTheme.ELECTRIC: {
                'name': 'Electric',
                'base_hues': [240, 60, 0, 180, 120, 300, 30, 270],  # Blue, Yellow, Red, Cyan, Green, Magenta, Orange, Purple
                'saturation_range': {
                    ColorMode.FOREGROUND: (0.95, 1.0),
                    ColorMode.BACKGROUND: (0.6, 0.8),
                    ColorMode.MUTED: (0.7, 0.9),
                    ColorMode.GLOW: (0.5, 0.75)
                },
                'lightness_range': {
                    ColorMode.FOREGROUND: (0.5, 0.9),
                    ColorMode.BACKGROUND: (0.15, 0.3),
                    ColorMode.MUTED: (0.35, 0.55),
                    ColorMode.GLOW: (0.4, 0.65)
                },
                'accent_colors': ['#0080ff', '#ffff00', '#ff0040', '#00ffff']
            },
            NeonTheme.PLASMA: {
                'name': 'Plasma',
                'base_hues': [280, 320, 0, 40, 260, 300, 20, 340],  # Purple, Pink, Red, Orange, Blue-purple, Magenta, Red-orange, Hot pink
                'saturation_range': {
                    ColorMode.FOREGROUND: (0.85, 1.0),
                    ColorMode.BACKGROUND: (0.5, 0.75),
                    ColorMode.MUTED: (0.6, 0.85),
                    ColorMode.GLOW: (0.4, 0.7)
                },
                'lightness_range': {
                    ColorMode.FOREGROUND: (0.4, 0.85),
                    ColorMode.BACKGROUND: (0.12, 0.28),
                    ColorMode.MUTED: (0.3, 0.5),
                    ColorMode.GLOW: (0.35, 0.6)
                },
                'accent_colors': ['#8000ff', '#ff0080', '#ff4000', '#ff8000']
            },
            NeonTheme.AURORA: {
                'name': 'Aurora',
                'base_hues': [180, 120, 280, 200, 100, 320, 160, 240],  # Cyan, Green, Purple, Light blue, Lime, Pink, Teal, Blue
                'saturation_range': {
                    ColorMode.FOREGROUND: (0.7, 0.95),
                    ColorMode.BACKGROUND: (0.4, 0.65),
                    ColorMode.MUTED: (0.5, 0.8),
                    ColorMode.GLOW: (0.3, 0.6)
                },
                'lightness_range': {
                    ColorMode.FOREGROUND: (0.45, 0.85),
                    ColorMode.BACKGROUND: (0.1, 0.25),
                    ColorMode.MUTED: (0.32, 0.52),
                    ColorMode.GLOW: (0.38, 0.62)
                },
                'accent_colors': ['#00ffff', '#00ff80', '#8080ff', '#80ff80']
            }
        }
    
    def generate(self, count: int, theme: Union[NeonTheme, str] = NeonTheme.CYBER, 
                method: str = 'balanced', mode: ColorMode = ColorMode.FOREGROUND) -> NeonPalette:
        """
        Generate a neon color palette
        
        Args:
            count: Number of colors to generate
            theme: Theme to use (NeonTheme enum or string)
            method: Generation method ('balanced', 'rainbow', 'monochrome', 'complementary', 'triadic', 'random', 'gradient')
            mode: Color mode (foreground, background, muted, glow)
        
        Returns:
            NeonPalette object containing the generated colors
        """
        if isinstance(theme, str):
            theme = NeonTheme(theme)
        
        theme_data = self.themes[theme]
        
        if method == 'balanced':
            colors = self._generate_balanced(count, theme_data, mode)
        elif method == 'rainbow':
            colors = self._generate_rainbow(count, theme_data, mode)
        elif method == 'monochrome':
            colors = self._generate_monochrome(count, theme_data, mode)
        elif method == 'complementary':
            colors = self._generate_complementary(count, theme_data, mode)
        elif method == 'triadic':
            colors = self._generate_triadic(count, theme_data, mode)
        elif method == 'random':
            colors = self._generate_random(count, theme_data, mode)
        elif method == 'gradient':
            colors = self._generate_gradient(count, theme_data, mode)
        else:
            colors = self._generate_balanced(count, theme_data, mode)
        
        return NeonPalette(colors, theme_data['name'], theme, mode)
    
    def _get_ranges(self, theme_data: Dict, mode: ColorMode) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Get saturation and lightness ranges for given mode"""
        sat_range = theme_data['saturation_range'][mode]
        light_range = theme_data['lightness_range'][mode]
        return sat_range, light_range
    
    def _generate_balanced(self, count: int, theme_data: Dict, mode: ColorMode) -> List[NeonColor]:
        """Generate balanced colors using theme's base hues"""
        colors = []
        base_hues = theme_data['base_hues']
        sat_range, light_range = self._get_ranges(theme_data, mode)
        sat_min, sat_max = sat_range
        light_min, light_max = light_range
        
        for i in range(count):
            # Use base hues first, then interpolate
            if i < len(base_hues):
                hue = base_hues[i]
            else:
                # Interpolate between base hues
                base_idx = i % len(base_hues)
                next_idx = (base_idx + 1) % len(base_hues)
                factor = (i - base_idx) / len(base_hues)
                hue = self._interpolate_hue(base_hues[base_idx], base_hues[next_idx], factor)
            
            # Vary saturation and lightness within mode constraints
            saturation = sat_min + (sat_max - sat_min) * (0.7 + 0.3 * math.sin(i * 0.5))
            lightness = light_min + (light_max - light_min) * (0.8 + 0.2 * math.cos(i * 0.7))
            
            r, g, b = colorsys.hls_to_rgb(hue/360, lightness, saturation)
            colors.append(NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=mode))
        
        return colors
    
    def _generate_rainbow(self, count: int, theme_data: Dict, mode: ColorMode) -> List[NeonColor]:
        """Generate rainbow spectrum with neon intensity"""
        colors = []
        sat_range, light_range = self._get_ranges(theme_data, mode)
        sat_min, sat_max = sat_range
        light_min, light_max = light_range
        
        for i in range(count):
            hue = (i * 360 / count) % 360
            saturation = (sat_min + sat_max) / 2
            lightness = (light_min + light_max) / 2
            
            r, g, b = colorsys.hls_to_rgb(hue/360, lightness, saturation)
            colors.append(NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=mode))
        
        return colors
    
    def _generate_monochrome(self, count: int, theme_data: Dict, mode: ColorMode) -> List[NeonColor]:
        """Generate monochrome variations of a single hue"""
        colors = []
        base_hue = theme_data['base_hues'][0]  # Use first hue
        sat_range, light_range = self._get_ranges(theme_data, mode)
        sat_min, sat_max = sat_range
        light_min, light_max = light_range
        
        for i in range(count):
            # Vary saturation and lightness
            saturation = sat_min + (sat_max - sat_min) * (i / max(1, count - 1))
            lightness = light_min + (light_max - light_min) * ((count - 1 - i) / max(1, count - 1))
            
            r, g, b = colorsys.hls_to_rgb(base_hue/360, lightness, saturation)
            colors.append(NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=mode))
        
        return colors
    
    def _generate_complementary(self, count: int, theme_data: Dict, mode: ColorMode) -> List[NeonColor]:
        """Generate complementary color pairs"""
        colors = []
        base_hue = theme_data['base_hues'][0]
        complement_hue = (base_hue + 180) % 360
        sat_range, light_range = self._get_ranges(theme_data, mode)
        sat_min, sat_max = sat_range
        light_min, light_max = light_range
        
        for i in range(count):
            # Alternate between base and complement
            hue = base_hue if i % 2 == 0 else complement_hue
            
            # Vary intensity
            saturation = sat_min + (sat_max - sat_min) * (0.8 + 0.2 * math.sin(i))
            lightness = light_min + (light_max - light_min) * (0.7 + 0.3 * math.cos(i))
            
            r, g, b = colorsys.hls_to_rgb(hue/360, lightness, saturation)
            colors.append(NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=mode))
        
        return colors
    
    def _generate_triadic(self, count: int, theme_data: Dict, mode: ColorMode) -> List[NeonColor]:
        """Generate triadic color harmony"""
        colors = []
        base_hue = theme_data['base_hues'][0]
        hues = [base_hue, (base_hue + 120) % 360, (base_hue + 240) % 360]
        sat_range, light_range = self._get_ranges(theme_data, mode)
        sat_min, sat_max = sat_range
        light_min, light_max = light_range
        
        for i in range(count):
            hue = hues[i % 3]
            
            # Vary intensity
            saturation = sat_min + (sat_max - sat_min) * (0.8 + 0.2 * math.sin(i * 0.8))
            lightness = light_min + (light_max - light_min) * (0.7 + 0.3 * math.cos(i * 0.6))
            
            r, g, b = colorsys.hls_to_rgb(hue/360, lightness, saturation)
            colors.append(NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=mode))
        
        return colors
    
    def _generate_random(self, count: int, theme_data: Dict, mode: ColorMode) -> List[NeonColor]:
        """Generate random colors within theme constraints"""
        colors = []
        base_hues = theme_data['base_hues']
        sat_range, light_range = self._get_ranges(theme_data, mode)
        sat_min, sat_max = sat_range
        light_min, light_max = light_range
        
        for i in range(count):
            # Random hue from base hues with some variation
            base_hue = random.choice(base_hues)
            hue = (base_hue + random.uniform(-30, 30)) % 360
            
            saturation = random.uniform(sat_min, sat_max)
            lightness = random.uniform(light_min, light_max)
            
            r, g, b = colorsys.hls_to_rgb(hue/360, lightness, saturation)
            colors.append(NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=mode))
        
        return colors
    
    def _generate_gradient(self, count: int, theme_data: Dict, mode: ColorMode) -> List[NeonColor]:
        """Generate smooth gradient between accent colors"""
        accent_colors = [NeonColor.from_hex(hex_color, mode=mode) for hex_color in theme_data['accent_colors']]
        
        # Convert accent colors to the requested mode
        if mode == ColorMode.BACKGROUND:
            accent_colors = [color.to_background() for color in accent_colors]
        elif mode == ColorMode.MUTED:
            accent_colors = [color.to_muted() for color in accent_colors]
        elif mode == ColorMode.GLOW:
            accent_colors = [color.to_glow() for color in accent_colors]
        
        return self._interpolate_colors(accent_colors, count)
    
    def _interpolate_colors(self, colors: List[NeonColor], count: int) -> List[NeonColor]:
        """Interpolate between existing colors to create more"""
        if count <= len(colors):
            return colors[:count]
        
        result = []
        segments = count - 1
        colors_per_segment = segments / (len(colors) - 1)
        
        for i in range(count):
            if i == 0:
                result.append(colors[0])
            elif i == count - 1:
                result.append(colors[-1])
            else:
                # Find which segment we're in
                segment_pos = i / segments * (len(colors) - 1)
                segment_idx = int(segment_pos)
                segment_frac = segment_pos - segment_idx
                
                if segment_idx >= len(colors) - 1:
                    result.append(colors[-1])
                else:
                    # Interpolate in HSL space
                    color1 = colors[segment_idx]
                    color2 = colors[segment_idx + 1]
                    
                    h1, s1, l1 = color1.hsl
                    h2, s2, l2 = color2.hsl
                    
                    # Handle hue wraparound
                    if abs(h2 - h1) > 0.5:
                        if h1 > h2:
                            h2 += 1.0
                        else:
                            h1 += 1.0
                    
                    h = (h1 + (h2 - h1) * segment_frac) % 1.0
                    s = s1 + (s2 - s1) * segment_frac
                    l = l1 + (l2 - l1) * segment_frac
                    
                    r, g, b = colorsys.hls_to_rgb(h, l, s)
                    new_color = NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=color1.mode)
                    result.append(new_color)
        
        return result
    
    def _create_variations(self, colors: List[NeonColor], count: int) -> List[NeonColor]:
        """Create variations of existing colors"""
        result = list(colors)
        
        while len(result) < count:
            base_color = random.choice(colors)
            
            # Create variation based on current mode
            if base_color.mode == ColorMode.BACKGROUND:
                variation_type = random.choice(['lighten', 'darken', 'saturate', 'hue_shift'])
                factor_range = (0.8, 1.2)  # Smaller variations for backgrounds
            else:
                variation_type = random.choice(['brighten', 'darken', 'saturate', 'desaturate', 'hue_shift'])
                factor_range = (0.7, 1.3)
            
            if variation_type == 'brighten' or variation_type == 'lighten':
                new_color = base_color.brighten(random.uniform(1.1, factor_range[1]))
            elif variation_type == 'darken':
                new_color = base_color.darken(random.uniform(factor_range[0], 0.9))
            elif variation_type == 'saturate':
                new_saturation = min(1.0, base_color.hsl[1] * random.uniform(1.1, 1.2))
                new_color = base_color.with_saturation(new_saturation)
            elif variation_type == 'desaturate':
                min_sat = 0.3 if base_color.mode == ColorMode.BACKGROUND else 0.5
                new_saturation = max(min_sat, base_color.hsl[1] * random.uniform(0.8, 0.9))
                new_color = base_color.with_saturation(new_saturation)
            else:  # hue_shift
                h, s, l = base_color.hsl
                shift_amount = 0.05 if base_color.mode == ColorMode.BACKGROUND else 0.1
                new_h = (h + random.uniform(-shift_amount, shift_amount)) % 1.0
                r, g, b = colorsys.hls_to_rgb(new_h, l, s)
                new_color = NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=base_color.mode)
            
            result.append(new_color)
        
        return result[:count]
    
    def _extend_harmony(self, colors: List[NeonColor], count: int) -> List[NeonColor]:
        """Extend using color harmony rules"""
        result = list(colors)
        
        while len(result) < count:
            base_color = random.choice(colors)
            h, s, l = base_color.hsl
            
            # Create harmonious color
            harmony_type = random.choice(['split_complement', 'analogous', 'tetrad'])
            
            if harmony_type == 'split_complement':
                new_h = (h + random.choice([150, 210]) / 360) % 1.0
            elif harmony_type == 'analogous':
                shift = 30 if base_color.mode == ColorMode.BACKGROUND else 60
                new_h = (h + random.uniform(-shift, shift) / 360) % 1.0
            else:  # tetrad
                new_h = (h + random.choice([90, 180, 270]) / 360) % 1.0
            
            r, g, b = colorsys.hls_to_rgb(new_h, l, s)
            result.append(NeonColor.from_rgb(int(r*255), int(g*255), int(b*255), mode=base_color.mode))
        
        return result[:count]
    
    def _interpolate_hue(self, hue1: float, hue2: float, factor: float) -> float:
        """Interpolate between two hues, handling wraparound"""
        diff = hue2 - hue1
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        
        return (hue1 + diff * factor) % 360
    
    def get_theme_names(self) -> List[str]:
        """Get list of available theme names"""
        return [theme.value for theme in NeonTheme]
    
    def create_custom_theme(self, name: str, base_hues: List[float], 
                           saturation_ranges: Dict[ColorMode, Tuple[float, float]] = None,
                           lightness_ranges: Dict[ColorMode, Tuple[float, float]] = None,
                           accent_colors: List[str] = None) -> str:
        """Create a custom theme"""
        if accent_colors is None:
            accent_colors = []
        
        if saturation_ranges is None:
            saturation_ranges = {
                ColorMode.FOREGROUND: (0.8, 1.0),
                ColorMode.BACKGROUND: (0.4, 0.7),
                ColorMode.MUTED: (0.5, 0.8),
                ColorMode.GLOW: (0.3, 0.6)
            }
        
        if lightness_ranges is None:
            lightness_ranges = {
                ColorMode.FOREGROUND: (0.5, 0.9),
                ColorMode.BACKGROUND: (0.1, 0.25),
                ColorMode.MUTED: (0.3, 0.5),
                ColorMode.GLOW: (0.35, 0.6)
            }
        
        # Add custom theme to themes dict
        custom_theme = f"custom_{name.lower()}"
        self.themes[custom_theme] = {
            'name': name,
            'base_hues': base_hues,
            'saturation_range': saturation_ranges,
            'lightness_range': lightness_ranges,
            'accent_colors': accent_colors
        }
        
        return custom_theme


# Enhanced convenience functions for quick usage
def neon_colors(count: int, theme: str = 'cyber', method: str = 'balanced', mode: str = 'foreground') -> List[str]:
    """Quick function to get hex color list"""
    generator = NeonGenerator()
    color_mode = ColorMode(mode)
    palette = generator.generate(count, theme, method, color_mode)
    return palette.hex_colors()


def neon_rgb(count: int, theme: str = 'cyber', method: str = 'balanced', mode: str = 'foreground') -> List[Tuple[int, int, int]]:
    """Quick function to get RGB color list"""
    generator = NeonGenerator()
    color_mode = ColorMode(mode)
    palette = generator.generate(count, theme, method, color_mode)
    return palette.rgb_colors()

# neon_pallete.py
import colorsys
import random

import colorsys
import random

def generate_golden_ratio_colors(n, saturation=0.85, value=0.95):
    """
    Generates distinct, high-contrast neon colors using the Golden Ratio.
    This prevents 'muddy' colors and ensures neighbors are visually distinct.
    
    Args:
        n (int): Number of colors to generate.
        saturation (float): 0.0 to 1.0 (Color intensity).
        value (float): 0.0 to 1.0 (Brightness/Lightness).
    """
    golden_ratio_conjugate = 0.618033988749895
    h = random.random() # Random start
    colors = []
    
    for _ in range(n):
        h += golden_ratio_conjugate
        h %= 1
        # Convert Hsv to Rgb
        r, g, b = colorsys.hsv_to_rgb(h, saturation, value)
        # Convert to Hex
        hex_code = '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))
        colors.append(hex_code)
        
    return colors

def neon_background_colors(n):
    """
    Generates colors suitable for BACKGROUNDS in the TUI.
    These must be darker/dimmer so that White/Light text is readable on top of them.
    Value is lowered to 0.35 to ensure contrast.
    """
    # High saturation keeps them colorful, Low value makes them dark enough for white text
    return generate_golden_ratio_colors(n, saturation=0.7, value=0.35)

def generate_text_colors(n):
    """
    Generates colors suitable for TEXT in the SVG.
    These must be very bright/high value to pop against a dark background.
    """
    # High saturation and Max value for "Neon Glow" effect
    return generate_golden_ratio_colors(n, saturation=0.9, value=1.0)

def neon_terminal_pair(count: int, theme: str = 'cyber', method: str = 'balanced') -> Tuple[List[str], List[str]]:
    """Get matching foreground and background color pairs for terminal use"""
    generator = NeonGenerator()
    
    # Generate background colors
    bg_palette = generator.generate(count, theme, method, ColorMode.BACKGROUND)
    
    # Generate foreground colors
    fg_palette = generator.generate(count, theme, method, ColorMode.FOREGROUND)
    
    return fg_palette.hex_colors(), bg_palette.hex_colors()


def demo_all_modes():
    """Demo function showing all themes and modes"""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
        from rich.panel import Panel
        
        console = Console()
        generator = NeonGenerator()
        
        console.print(Panel.fit("🌈 Enhanced Neon Color Generator Demo", style="bold bright_magenta"))
        
        for theme in [NeonTheme.CYBER, NeonTheme.SYNTHWAVE, NeonTheme.MATRIX]:
            console.print(f"\n[bold cyan]Theme: {theme.value.title()}[/bold cyan]")
            
            table = Table(title=f"Color Modes", box=None, show_header=True)
            table.add_column("Mode", style="cyan", width=12)
            table.add_column("Colors (6)", width=40)
            table.add_column("Description", width=30)
            
            modes = [
                (ColorMode.FOREGROUND, "Bright colors for text/highlights"),
                (ColorMode.BACKGROUND, "Dark colors for backgrounds"),
                (ColorMode.MUTED, "Medium intensity for accents"),
                (ColorMode.GLOW, "Soft glowing effect")
            ]
            
            for mode, description in modes:
                palette = generator.generate(6, theme, 'balanced', mode)
                color_display = Text()
                
                for color in palette:
                    color_display.append("███ ", style=color.hex)
                
                table.add_row(mode.value, color_display, description)
            
            console.print(table)
            
            # Show terminal pairing example
            fg_colors, bg_colors = neon_terminal_pair(3, theme.value)
            console.print(f"\n[bold green]Terminal Pairing Example:[/bold green]")
            pairing_text = Text()
            for i, (fg, bg) in enumerate(zip(fg_colors, bg_colors)):
                pairing_text.append(f" Text {i+1} ", style=f"{fg} on {bg}")
                pairing_text.append(" ")
            console.print(pairing_text)
            
    except ImportError:
        print("Install 'rich' to see colored demo: pip install rich")
        
        # Fallback text demo
        generator = NeonGenerator()
        for theme in [NeonTheme.CYBER, NeonTheme.SYNTHWAVE, NeonTheme.MATRIX]:
            print(f"\n=== {theme.value.upper()} THEME ===")
            
            for mode in ColorMode:
                palette = generator.generate(6, theme, 'balanced', mode)
                colors = [color.hex for color in palette]
                print(f"{mode.value.capitalize()}: {', '.join(colors)}")
            
            # Terminal pairing
            fg_colors, bg_colors = neon_terminal_pair(3, theme.value)
            print(f"Terminal pairs: {list(zip(fg_colors, bg_colors))}")


def demo_terminal_usage():
    """Demo specifically for terminal background usage"""
    print("=== TERMINAL BACKGROUND COLOR DEMO ===")
    print("Perfect for terminal applications, syntax highlighting, and UI backgrounds\n")
    
    generator = NeonGenerator()
    
    themes_to_show = ['cyber', 'matrix', 'synthwave', 'miami']
    
    for theme in themes_to_show:
        print(f"Theme: {theme.upper()}")
        
        # Background colors
        bg_colors = neon_background_colors(8, theme)
        print(f"Background colors: {bg_colors}")
        
        # Show contrast ratios with white text
        white = NeonColor.from_hex("#ffffff")
        bg_palette = generator.generate(8, theme, 'balanced', ColorMode.BACKGROUND)
        
        readable_count = sum(1 for color in bg_palette if white.is_readable_on(color))
        print(f"Colors readable with white text: {readable_count}/8")
        
        # Terminal pairs
        fg_colors, bg_colors_paired = neon_terminal_pair(4, theme)
        print(f"Terminal pairs (fg, bg): {list(zip(fg_colors, bg_colors_paired))}")
        print()


if __name__ == "__main__":
    demo_all_modes()
    print("\n" + "="*60 + "\n")
    demo_terminal_usage()
