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
    
    # Start background notification checker
    notification_service.start_background_checker(page)

    def tab_change(e):
        # Refresh content when switching tabs if needed
        pass

    tabs = ft.Tabs(
        selected_index=0, 
        animation_duration=300, 
        on_change=tab_change,
        expand=True,
        tabs=[
            ft.Tab(
                text="Home", 
                icon=ft.Icons.HOME, 
                content=ft.Container(
                    content=ft.Text("Welcome to the Finance Manager!"),
                    padding=20,
                )
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
