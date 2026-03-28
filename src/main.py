import flet as ft
from pages.transactions import transactions_tab
from pages.categories import categories_tab
from pages.bills import bills_tab
from pages.dashboard import dashboard_tab
from services.notifications import notification_service

def main(page: ft.Page):
    page.title = "Pennywise - Bill Tracker"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START
    page.theme = ft.Theme(color_scheme_seed="indigo")
    page.theme_mode = ft.ThemeMode.SYSTEM

    # Start background notification checker
    notification_service.start_background_checker(page)

    def tab_change(e):
        pass

    home_content = ft.Container(
        content=ft.Column(
            [
                ft.Text("Pennywise", size=36, weight=ft.FontWeight.BOLD),
                ft.Text("Your personal bill tracker", size=15, color="grey"),
                ft.Divider(height=24),
                ft.Text(
                    "Import your bank transactions, then let Pennywise detect your recurring "
                    "bills automatically — or create them yourself from any payment.",
                    size=13,
                ),
                ft.Divider(height=16),
                ft.Column(
                    [
                        ft.Row([ft.Icon(ft.Icons.LIST, color="indigo", size=18),
                                ft.Text("Transactions — import CSV and manage your payment history", size=13)]),
                        ft.Row([ft.Icon(ft.Icons.RECEIPT_LONG, color="indigo", size=18),
                                ft.Text("Bills — review auto-detected bills or create one from any payment", size=13)]),
                        ft.Row([ft.Icon(ft.Icons.CATEGORY, color="indigo", size=18),
                                ft.Text("Categories — organise bills and transactions by type", size=13)]),
                        ft.Row([ft.Icon(ft.Icons.DASHBOARD, color="indigo", size=18),
                                ft.Text("Dashboard — see what's due, overdue, and paid at a glance", size=13)]),
                    ],
                    spacing=12,
                ),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(32),
        max_width=580,
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
