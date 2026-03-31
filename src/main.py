import flet as ft
from pages.transactions import transactions_tab
from pages.categories import categories_tab
from pages.bills import bills_tab
from pages.dashboard import dashboard_tab
from services.notifications import notification_service
from theme import COLORS, setup_theme, neon_card, neon_divider, section_header, mono_text

def main(page: ft.Page):
    page.title = "Pennywise - Bill Tracker"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START
    setup_theme(page)

    # Start background notification checker
    notification_service.start_background_checker(page)

    def tab_change(e):
        pass

    feature_items = [
        (ft.Icons.LIST,         COLORS.PRIMARY,   "Transactions",  "Import CSV and manage your payment history"),
        (ft.Icons.RECEIPT_LONG, COLORS.WARNING,   "Bills",         "Review auto-detected bills or create one from any payment"),
        (ft.Icons.CATEGORY,     COLORS.TEXT_DIM,  "Categories",    "Organise bills and transactions by type"),
        (ft.Icons.DASHBOARD,    COLORS.SUCCESS,   "Dashboard",     "See what's due, overdue, and paid at a glance"),
    ]

    feature_tiles = []
    for icon, color, label, desc in feature_items:
        feature_tiles.append(
            neon_card(
                ft.Row(
                    [
                        ft.Icon(icon, color=color, size=20),
                        ft.Column(
                            [
                                ft.Text(label, size=13, weight=ft.FontWeight.BOLD, color=color),
                                ft.Text(desc, size=11, color=COLORS.TEXT_DIM),
                            ],
                            spacing=2,
                            tight=True,
                        ),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                accent=COLORS.BORDER_DIM,
                padding=14,
            )
        )

    home_content = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "PENNYWISE",
                    size=38,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS.PRIMARY,
                    font_family="ShareTechMono",
                ),
                ft.Text(
                    "// your personal bill tracker",
                    size=13,
                    color=COLORS.TEXT_DIM,
                    font_family="ShareTechMono",
                ),
                neon_divider(COLORS.PRIMARY),
                ft.Text(
                    "Import your bank transactions, then let Pennywise detect your recurring "
                    "bills automatically — or create them yourself from any payment.",
                    size=13,
                    color=COLORS.TEXT_PRIMARY,
                ),
                neon_divider(COLORS.BORDER_DIM),
                ft.Column(feature_tiles, spacing=8),
            ],
            spacing=10,
        ),
        padding=ft.padding.all(32),
        width=580,
        bgcolor=COLORS.BACKGROUND,
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        on_change=tab_change,
        expand=True,
        tabs=[
            ft.Tab(
                text="Home",
                icon=ft.Icons.HOME,
                content=home_content,
            ),
            ft.Tab(
                text="Transactions",
                icon=ft.Icons.LIST,
                content=ft.Container(
                    content=transactions_tab(page),
                    padding=20,
                )
            ),
            ft.Tab(
                text="Categories",
                icon=ft.Icons.CATEGORY,
                content=ft.Container(
                    content=categories_tab(page),
                    padding=20,
                )
            ),
            ft.Tab(
                text="Bills",
                icon=ft.Icons.RECEIPT_LONG,
                content=ft.Container(
                    content=bills_tab(page),
                    padding=20,
                )
            ),
            ft.Tab(
                text="Dashboard",
                icon=ft.Icons.DASHBOARD,
                content=ft.Container(
                    content=dashboard_tab(page),
                    padding=20,
                )
            ),
        ]
    )

    page.add(tabs)

ft.app(main)
