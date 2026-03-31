"""
Bill Dashboard Page

Provides overview of bill status, upcoming payments, and key metrics.
Shows summary information and recent activity for bill management.
"""

import flet as ft
from datetime import date, timedelta
from services.db import session, Bill, BillInstance
from services.notifications import notification_service
from theme import (
    COLORS, neon_card, neon_divider, section_header, mono_text, cyber_button
)


def dashboard_tab(page: ft.Page):
    """Main dashboard tab showing bill summary and stats"""

    def refresh_dashboard():
        """Refresh all dashboard data"""
        try:
            summary = notification_service.get_dashboard_summary()

            # Update summary cards (count at index 1, amount at index 2)
            upcoming_card.content.content.controls[1].value = str(summary['upcoming_count'])
            upcoming_card.content.content.controls[2].value = f"${summary['upcoming_total']:.2f}"

            overdue_card.content.content.controls[1].value = str(summary['overdue_count'])
            overdue_card.content.content.controls[2].value = f"${summary['overdue_total']:.2f}"

            today_card.content.content.controls[1].value = str(summary['today_count'])

            # Update today's bills list
            today_bills_list.controls.clear()
            for bill_instance in summary['today_bills']:
                bill = bill_instance.bill
                today_bills_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(bill.payee, size=13, color=COLORS.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                                        mono_text(f"${bill.expected_amount:.2f}", color=COLORS.WARNING, size=12),
                                    ],
                                    spacing=2,
                                    tight=True,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CHECK_CIRCLE,
                                    icon_color=COLORS.SUCCESS,
                                    tooltip="Mark as Paid",
                                    on_click=lambda e, instance_id=bill_instance.id: mark_paid(instance_id)
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=COLORS.SURFACE,
                        border=ft.border.all(1, COLORS.BORDER_DIM),
                        border_radius=4,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        margin=ft.margin.only(bottom=6),
                    )
                )

            if not summary['today_bills']:
                today_bills_list.controls.append(
                    ft.Text("No bills due today", size=12, color=COLORS.TEXT_DIM, font_family="ShareTechMono")
                )

            # Refresh overdue and upcoming tables
            refresh_overdue_table()
            refresh_upcoming_table()

            page.update()

        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error refreshing dashboard: {e}")))

    def refresh_overdue_table():
        """Refresh the overdue bills table"""
        try:
            overdue_bills = session.query(BillInstance).join(Bill).filter(
                BillInstance.due_date < date.today(),
                BillInstance.status == 'pending',
                Bill.is_active == True
            ).order_by(BillInstance.due_date).all()

            overdue_table.rows.clear()

            if overdue_bills:
                overdue_status.value = f"{len(overdue_bills)} overdue bill(s)"
                overdue_status.color = COLORS.SECONDARY
            else:
                overdue_status.value = "No overdue bills"
                overdue_status.color = COLORS.SUCCESS

            for bill_instance in overdue_bills:
                bill = bill_instance.bill
                days_overdue = (date.today() - bill_instance.due_date).days
                overdue_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(bill.payee, color=COLORS.TEXT_PRIMARY, size=13)),
                        ft.DataCell(mono_text(f"${bill.expected_amount:.2f}", color=COLORS.TEXT_PRIMARY)),
                        ft.DataCell(mono_text(bill_instance.due_date.strftime("%Y-%m-%d"), color=COLORS.SECONDARY)),
                        ft.DataCell(mono_text(f"{days_overdue}d overdue", color=COLORS.SECONDARY)),
                        ft.DataCell(ft.IconButton(
                            icon=ft.Icons.CHECK_CIRCLE,
                            icon_color=COLORS.SUCCESS,
                            tooltip="Mark as Paid",
                            on_click=lambda e, instance_id=bill_instance.id: mark_paid(instance_id)
                        )),
                    ])
                )

            page.update()

        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error loading overdue bills: {e}")))

    def refresh_upcoming_table():
        """Refresh the upcoming bills table"""
        try:
            end_date = date.today() + timedelta(days=30)
            upcoming_bills = session.query(BillInstance).join(Bill).filter(
                BillInstance.due_date <= end_date,
                BillInstance.due_date >= date.today(),
                BillInstance.status == 'pending',
                Bill.is_active == True
            ).order_by(BillInstance.due_date).limit(10).all()

            upcoming_table.rows.clear()

            for bill_instance in upcoming_bills:
                bill = bill_instance.bill
                days_until = (bill_instance.due_date - date.today()).days

                if days_until == 0:
                    urgency_color = COLORS.SECONDARY
                    urgency_text = "TODAY"
                elif days_until <= 3:
                    urgency_color = COLORS.WARNING
                    urgency_text = f"{days_until}d"
                else:
                    urgency_color = COLORS.SUCCESS
                    urgency_text = f"{days_until}d"

                upcoming_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(bill.payee, color=COLORS.TEXT_PRIMARY, size=13)),
                        ft.DataCell(mono_text(f"${bill.expected_amount:.2f}", color=COLORS.TEXT_PRIMARY)),
                        ft.DataCell(mono_text(bill_instance.due_date.strftime("%Y-%m-%d"), color=COLORS.TEXT_DIM)),
                        ft.DataCell(mono_text(urgency_text, color=urgency_color)),
                        ft.DataCell(ft.IconButton(
                            icon=ft.Icons.CHECK_CIRCLE,
                            icon_color=COLORS.SUCCESS,
                            tooltip="Mark as Paid",
                            on_click=lambda e, instance_id=bill_instance.id: mark_paid(instance_id)
                        ))
                    ])
                )

            page.update()

        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error loading upcoming bills: {e}")))

    def mark_paid(bill_instance_id):
        """Mark a bill instance as paid"""
        try:
            success = notification_service.mark_bill_paid(bill_instance_id)
            if success:
                page.open(ft.SnackBar(content=ft.Text("Bill marked as paid")))
                refresh_dashboard()
            else:
                page.open(ft.SnackBar(content=ft.Text("Error marking bill as paid")))
        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error: {e}")))

    def check_notifications():
        """Manually check for notifications"""
        try:
            notification_service.check_and_notify(page)
        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error checking notifications: {e}")))

    # -----------------------------------------------------------------------
    # Summary cards
    # Note: count at controls[1], amount at controls[2] — refresh_dashboard()
    # depends on these indices.
    # -----------------------------------------------------------------------

    upcoming_card = neon_card(
        ft.Column(
            [
                ft.Icon(ft.Icons.UPCOMING, color=COLORS.PRIMARY, size=28),
                mono_text("0", color=COLORS.PRIMARY, size=34),
                mono_text("$0.00", color=COLORS.PRIMARY, size=14),
                ft.Text("Upcoming Bills", size=12, weight=ft.FontWeight.W_500, color=COLORS.TEXT_PRIMARY),
                ft.Text("Next 30 days", size=11, color=COLORS.TEXT_DIM),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        accent=COLORS.PRIMARY,
        width=190,
        padding=ft.padding.symmetric(vertical=20, horizontal=24),
    )

    overdue_card = neon_card(
        ft.Column(
            [
                ft.Icon(ft.Icons.WARNING_ROUNDED, color=COLORS.SECONDARY, size=28),
                mono_text("0", color=COLORS.SECONDARY, size=34),
                mono_text("$0.00", color=COLORS.SECONDARY, size=14),
                ft.Text("Overdue Bills", size=12, weight=ft.FontWeight.W_500, color=COLORS.TEXT_PRIMARY),
                ft.Text("Past due", size=11, color=COLORS.TEXT_DIM),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        accent=COLORS.SECONDARY,
        width=190,
        padding=ft.padding.symmetric(vertical=20, horizontal=24),
    )

    today_card = neon_card(
        ft.Column(
            [
                ft.Icon(ft.Icons.TODAY, color=COLORS.WARNING, size=28),
                mono_text("0", color=COLORS.WARNING, size=34),
                ft.Text("Due Today", size=12, weight=ft.FontWeight.W_500, color=COLORS.TEXT_PRIMARY),
                ft.Text("Action needed", size=11, color=COLORS.TEXT_DIM),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        accent=COLORS.WARNING,
        width=190,
        padding=ft.padding.symmetric(vertical=20, horizontal=24),
    )

    # Action buttons
    refresh_button = cyber_button("Refresh", icon=ft.Icons.REFRESH, on_click=lambda _: refresh_dashboard())
    notifications_button = cyber_button(
        "Check Notifications",
        icon=ft.Icons.NOTIFICATIONS,
        on_click=lambda _: check_notifications(),
        color=COLORS.TEXT_DIM,
    )

    # Overdue bills table
    overdue_status = ft.Text("", size=12, font_family="ShareTechMono")
    overdue_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("PAYEE", size=11, color=COLORS.TEXT_DIM)),
            ft.DataColumn(ft.Text("AMOUNT", size=11, color=COLORS.TEXT_DIM)),
            ft.DataColumn(ft.Text("DUE DATE", size=11, color=COLORS.TEXT_DIM)),
            ft.DataColumn(ft.Text("OVERDUE", size=11, color=COLORS.TEXT_DIM)),
            ft.DataColumn(ft.Text("ACTION", size=11, color=COLORS.TEXT_DIM)),
        ],
        width=800,
        heading_row_color=COLORS.SURFACE_VARIANT,
        data_row_color={ft.ControlState.HOVERED: f"{COLORS.PRIMARY}11"},
    )

    # Today's bills section
    today_bills_list = ft.Column()

    # Upcoming bills table
    upcoming_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("PAYEE", size=11, color=COLORS.TEXT_DIM)),
            ft.DataColumn(ft.Text("AMOUNT", size=11, color=COLORS.TEXT_DIM)),
            ft.DataColumn(ft.Text("DUE DATE", size=11, color=COLORS.TEXT_DIM)),
            ft.DataColumn(ft.Text("DAYS", size=11, color=COLORS.TEXT_DIM)),
            ft.DataColumn(ft.Text("ACTION", size=11, color=COLORS.TEXT_DIM)),
        ],
        width=800,
        heading_row_color=COLORS.SURFACE_VARIANT,
        data_row_color={ft.ControlState.HOVERED: f"{COLORS.PRIMARY}11"},
    )

    # Initial load
    refresh_dashboard()

    return ft.Column([
        section_header("Dashboard"),
        neon_divider(),

        # Summary cards row
        ft.Row([
            upcoming_card,
            overdue_card,
            today_card,
        ], alignment=ft.MainAxisAlignment.START, spacing=12),

        ft.Row([refresh_button, notifications_button], spacing=8),

        neon_divider(COLORS.BORDER_DIM),

        # Overdue bills section
        ft.Row([
            section_header("Overdue Bills", color=COLORS.SECONDARY),
            overdue_status,
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        neon_card(
            ft.ListView(controls=[overdue_table], height=200, auto_scroll=True),
            accent=COLORS.SECONDARY,
            padding=0,
        ),

        neon_divider(COLORS.BORDER_DIM),

        # Two-column layout
        ft.Row([
            # Left — Today's bills
            ft.Column([
                section_header("Bills Due Today", color=COLORS.WARNING),
                ft.Container(
                    content=today_bills_list,
                    height=220,
                    width=320,
                )
            ], spacing=10),

            # Right — Upcoming bills
            ft.Column([
                section_header("Upcoming (Next 30 Days)"),
                neon_card(
                    ft.Container(content=upcoming_table, height=280),
                    accent=COLORS.PRIMARY,
                    padding=0,
                ),
            ], spacing=10),
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START, spacing=32),

    ], scroll=ft.ScrollMode.AUTO, spacing=12)
