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
            
            # Update summary cards
            upcoming_card.content.content.controls[0].value = str(summary['upcoming_count'])
            upcoming_card.content.content.controls[1].value = f"${summary['upcoming_total']:.2f}"
            
            overdue_card.content.content.controls[0].value = str(summary['overdue_count'])
            overdue_card.content.content.controls[1].value = f"${summary['overdue_total']:.2f}"
            
            today_card.content.content.controls[0].value = str(summary['today_count'])
            
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
            
            # Refresh upcoming bills table
            refresh_upcoming_table()
            
            page.update()
            
        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error refreshing dashboard: {e}")))
    
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
    upcoming_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("0", size=30, weight=ft.FontWeight.BOLD, color="blue"),
                ft.Text("$0.00", size=16),
                ft.Text("Upcoming Bills", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("Next 30 days", size=12, color="grey")
            ], alignment=ft.MainAxisAlignment.CENTER,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            width=150,
            height=120
        )
    )
    
    overdue_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("0", size=30, weight=ft.FontWeight.BOLD, color="red"),
                ft.Text("$0.00", size=16),
                ft.Text("Overdue Bills", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("Past due", size=12, color="grey")
            ], alignment=ft.MainAxisAlignment.CENTER,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            width=150,
            height=120
        )
    )
    
    today_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("0", size=30, weight=ft.FontWeight.BOLD, color="orange"),
                ft.Text("Due Today", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("Action needed", size=12, color="grey")
            ], alignment=ft.MainAxisAlignment.CENTER,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            width=150,
            height=120
        )
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
        ft.Text("Bill Dashboard", size=20, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        
        # Summary cards row
        ft.Row([
            upcoming_card,
            overdue_card, 
            today_card
        ], alignment=ft.MainAxisAlignment.START),
        
        ft.Divider(),
        
        # Action buttons
        ft.Row([refresh_button, notifications_button]),
        
        ft.Divider(),
        
        # Two column layout
        ft.Row([
            # Left column - Today's bills  
            ft.Column([
                ft.Text("Bills Due Today", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=today_bills_list,
                    height=200,
                    width=300
                )
            ]),
            
            # Right column - Upcoming bills
            ft.Column([
                ft.Text("Upcoming Bills (Next 30 Days)", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=upcoming_table,
                    height=300
                )
            ])
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        
    ], scroll=ft.ScrollMode.AUTO)