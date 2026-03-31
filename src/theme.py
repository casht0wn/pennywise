"""
Cyberpunk / Neo-Tokyo theme for Pennywise.

Centralizes all color tokens and provides reusable builder helpers so no
color is ever hard-coded in page files.
"""

import flet as ft


# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------

class _Colors:
    BACKGROUND       = "#060b18"
    SURFACE          = "#0d1526"
    SURFACE_VARIANT  = "#121f38"

    PRIMARY          = "#00e5ff"   # neon cyan  — main accent
    SECONDARY        = "#ff0070"   # neon magenta — overdue / danger
    WARNING          = "#ffab00"   # electric amber — caution / due today
    SUCCESS          = "#00e676"   # neon lime  — paid / healthy

    TEXT_PRIMARY     = "#cdd8f5"
    TEXT_DIM         = "#4a6080"
    BORDER_DIM       = "#1a2d50"

COLORS = _Colors()


# ---------------------------------------------------------------------------
# Font registration
# ---------------------------------------------------------------------------

FONTS = {
    # Share Tech Mono — monospace, retro-futurist feel
    "ShareTechMono": (
        "https://fonts.gstatic.com/s/sharetechmono/v13/"
        "J7aHnp1uDWRBEqV98dVQztYldFcLowEF.woff2"
    ),
}


# ---------------------------------------------------------------------------
# Theme setup
# ---------------------------------------------------------------------------

def setup_theme(page: ft.Page) -> None:
    """Apply the cyberpunk dark theme to a Flet page."""
    page.fonts = FONTS
    page.bgcolor = COLORS.BACKGROUND
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(
        color_scheme_seed=COLORS.PRIMARY,
        color_scheme=ft.ColorScheme(
            primary=COLORS.PRIMARY,
            secondary=COLORS.WARNING,
            error=COLORS.SECONDARY,
            background=COLORS.BACKGROUND,
            surface=COLORS.SURFACE,
            surface_variant=COLORS.SURFACE_VARIANT,
            on_background=COLORS.TEXT_PRIMARY,
            on_surface=COLORS.TEXT_PRIMARY,
            on_primary="#000000",
            on_secondary="#000000",
        ),
    )


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

def neon_card(
    content: ft.Control,
    accent: str = COLORS.PRIMARY,
    width: int | None = None,
    padding: int = 20,
) -> ft.Container:
    """A dark container with a neon border and matching glow shadow."""
    return ft.Container(
        content=content,
        bgcolor=COLORS.SURFACE,
        border=ft.border.all(1, accent),
        border_radius=6,
        padding=padding,
        width=width,
        shadow=ft.BoxShadow(
            blur_radius=14,
            spread_radius=0,
            color=f"{accent}33",  # 20% alpha glow
            offset=ft.Offset(0, 0),
        ),
    )


def neon_divider(color: str = COLORS.PRIMARY, opacity: float = 0.3) -> ft.Container:
    """A slim neon horizontal rule."""
    return ft.Container(
        height=1,
        bgcolor=color,
        opacity=opacity,
        margin=ft.margin.symmetric(vertical=8),
    )


def section_header(text: str, color: str = COLORS.PRIMARY) -> ft.Row:
    """Section heading with a colored left accent bar."""
    return ft.Row(
        [
            ft.Container(width=3, height=22, bgcolor=color, border_radius=2),
            ft.Text(
                text.upper(),
                size=14,
                weight=ft.FontWeight.BOLD,
                color=color,
            ),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def mono_text(value: str, color: str = COLORS.TEXT_PRIMARY, size: int = 14) -> ft.Text:
    """Monospace text — used for financial values, dates, counts."""
    return ft.Text(value, color=color, size=size, font_family="ShareTechMono")


def cyber_button(
    text: str,
    icon: str | None = None,
    on_click=None,
    color: str = COLORS.PRIMARY,
) -> ft.OutlinedButton:
    """Outlined neon button — replaces ElevatedButton throughout the app."""
    style = ft.ButtonStyle(
        color=color,
        side=ft.BorderSide(1, color),
        shape=ft.RoundedRectangleBorder(radius=4),
        overlay_color=f"{color}1a",  # 10% tint on hover
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
    )
    if icon:
        return ft.OutlinedButton(
            text=text,
            icon=icon,
            icon_color=color,
            style=style,
            on_click=on_click,
        )
    return ft.OutlinedButton(text=text, style=style, on_click=on_click)


def status_badge(text: str, color: str) -> ft.Container:
    """Small pill badge with a neon border — for inline status indicators."""
    return ft.Container(
        content=ft.Text(text, size=11, color=color, font_family="ShareTechMono"),
        border=ft.border.all(1, color),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        bgcolor=f"{color}1a",
    )
