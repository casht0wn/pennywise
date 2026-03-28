"""
Bill Dashboard Page

Provides overview of bill status, upcoming payments, and key metrics.
Shows summary information and recent activity for bill management.
"""

import flet as ft
from datetime import date, timedelta
from services.db import session, Bill, BillInstance
from services.notifications import notification_service

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
                    ft.ListTile(
                        title=ft.Text(bill.payee),
                        subtitle=ft.Text(f"${bill.expected_amount:.2f}"),
                        trailing=ft.IconButton(
                            icon=ft.Icons.CHECK_CIRCLE,
                            icon_color="green",
                            tooltip="Mark as Paid",
                            on_click=lambda e, instance_id=bill_instance.id: mark_paid(instance_id)
                        )
                    )
                )
            
            if not summary['today_bills']:
                today_bills_list.controls.append(
                    ft.Text("No bills due today", style=ft.TextThemeStyle.BODY_MEDIUM)
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
                overdue_status.color = "red"
            else:
                overdue_status.value = "No overdue bills"
                overdue_status.color = "green"

            for bill_instance in overdue_bills:
                bill = bill_instance.bill
                days_overdue = (date.today() - bill_instance.due_date).days
                overdue_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(bill.payee)),
                        ft.DataCell(ft.Text(f"${bill.expected_amount:.2f}")),
                        ft.DataCell(ft.Text(bill_instance.due_date.strftime("%Y-%m-%d"), color="red")),
                        ft.DataCell(ft.Text(f"{days_overdue} day(s)", color="red")),
                        ft.DataCell(ft.IconButton(
                            icon=ft.Icons.CHECK_CIRCLE,
                            icon_color="green",
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
            # Get bills due in next 30 days
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

                # Color code by urgency
                if days_until == 0:
                    urgency_color = "red"
                    urgency_text = "TODAY"
                elif days_until <= 3:
                    urgency_color = "orange"
                    urgency_text = f"{days_until} days"
                else:
                    urgency_color = "green"
                    urgency_text = f"{days_until} days"

                upcoming_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(bill.payee)),
                        ft.DataCell(ft.Text(f"${bill.expected_amount:.2f}")),
                        ft.DataCell(ft.Text(bill_instance.due_date.strftime("%Y-%m-%d"))),
                        ft.DataCell(ft.Text(urgency_text, color=urgency_color)),
                        ft.DataCell(ft.IconButton(
                            icon=ft.Icons.CHECK_CIRCLE,
                            icon_color="green",
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
    
    # Create summary cards
    # Note: count is at controls[1], amount at controls[2] — refresh_dashboard() depends on these indices.
    upcoming_card = ft.Card(
        elevation=2,
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.UPCOMING, color="blue", size=28),
                    ft.Text("0", size=34, weight=ft.FontWeight.BOLD, color="blue"),
                    ft.Text("$0.00", size=14, color="blue700"),
                    ft.Text("Upcoming Bills", size=13, weight=ft.FontWeight.W_500),
                    ft.Text("Next 30 days", size=11, color="grey"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            ),
            padding=ft.padding.symmetric(vertical=20, horizontal=24),
            width=190,
        ),
    )

    overdue_card = ft.Card(
        elevation=2,
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.WARNING_ROUNDED, color="red", size=28),
                    ft.Text("0", size=34, weight=ft.FontWeight.BOLD, color="red"),
                    ft.Text("$0.00", size=14, color="red700"),
                    ft.Text("Overdue Bills", size=13, weight=ft.FontWeight.W_500),
                    ft.Text("Past due", size=11, color="grey"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            ),
            padding=ft.padding.symmetric(vertical=20, horizontal=24),
            width=190,
        ),
    )

    today_card = ft.Card(
        elevation=2,
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.TODAY, color="orange", size=28),
                    ft.Text("0", size=34, weight=ft.FontWeight.BOLD, color="orange"),
                    ft.Text("Due Today", size=13, weight=ft.FontWeight.W_500),
                    ft.Text("Action needed", size=11, color="grey"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            ),
            padding=ft.padding.symmetric(vertical=20, horizontal=24),
            width=190,
        ),
    )
    
    # Action buttons
    refresh_button = ft.ElevatedButton(
        "Refresh",
        icon=ft.Icons.REFRESH,
        on_click=lambda _: refresh_dashboard()
    )
    
    notifications_button = ft.ElevatedButton(
        "Check Notifications",
        icon=ft.Icons.NOTIFICATIONS,
        on_click=lambda _: check_notifications()
    )
    
    # Overdue bills table
    overdue_status = ft.Text("", size=12)
    overdue_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Payee")),
            ft.DataColumn(ft.Text("Amount")),
            ft.DataColumn(ft.Text("Due Date")),
            ft.DataColumn(ft.Text("Days Overdue")),
            ft.DataColumn(ft.Text("Action")),
        ],
        width=800,
    )

    # Today's bills section
    today_bills_list = ft.Column()

    # Upcoming bills table
    upcoming_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Payee")),
            ft.DataColumn(ft.Text("Amount")),
            ft.DataColumn(ft.Text("Due Date")),
            ft.DataColumn(ft.Text("Days Until")),
            ft.DataColumn(ft.Text("Action")),
        ],
        width=800
    )
    
    # Initial load
    refresh_dashboard()
    
    return ft.Column([
        ft.Text("Dashboard", size=20, weight=ft.FontWeight.BOLD),
        ft.Divider(),

        # Summary cards row
        ft.Row([
            upcoming_card,
            overdue_card,
            today_card,
        ], alignment=ft.MainAxisAlignment.START, spacing=12),

        ft.Row([refresh_button, notifications_button], spacing=8),

        ft.Divider(),

        # Overdue bills section
        ft.Row([
            ft.Text("Overdue Bills", size=16, weight=ft.FontWeight.BOLD, color="red"),
            overdue_status,
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.ListView(controls=[overdue_table], height=220, auto_scroll=True),

        ft.Divider(),

        # Two column layout
        ft.Row([
            # Left column - Today's bills
            ft.Column([
                ft.Text("Bills Due Today", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=today_bills_list,
                    height=200,
                    width=300,
                )
            ]),

            # Right column - Upcoming bills
            ft.Column([
                ft.Text("Upcoming Bills (Next 30 Days)", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(content=upcoming_table, height=300)
            ])
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        
    ], scroll=ft.ScrollMode.AUTO)