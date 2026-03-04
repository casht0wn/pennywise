"""
Notification System

Handles both in-app and system notifications for bill reminders.
- In-app alerts using Flet dialog boxes
- System notifications using plyer for cross-platform desktop alerts
- Daily check for upcoming bills with 3-5 day advance notice
"""

from datetime import date, timedelta
from typing import List, Optional
import threading
import time
import flet as ft
from plyer import notification

from services.db import session, Bill, BillInstance
from services.bill_detection import get_upcoming_bills, get_overdue_bills

class NotificationService:
    """Manages bill payment notifications"""
    
    def __init__(self):
        self.notification_enabled = True
        self.advance_days = 3  # Notify 3 days before due
        
    def show_system_notification(self, title: str, message: str):
        """Show desktop system notification"""
        if not self.notification_enabled:
            return
            
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Pennywise Bill Tracker",
                timeout=10  # seconds
            )
        except Exception as e:
            print(f"Failed to show system notification: {e}")
    
    def show_in_app_alert(self, page: ft.Page, title: str, message: str, on_close=None):
        """Show in-app alert dialog"""
        if not self.notification_enabled:
            return
            
        def close_alert(e):
            page.dialog.open = False
            page.update()
            if on_close:
                on_close()
        
        alert = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=close_alert)
            ]
        )
        
        page.dialog = alert
        alert.open = True
        page.update()
    
    def get_notification_messages(self) -> tuple[List[str], List[str]]:
        """
        Get notification messages for upcoming and overdue bills
        Returns: (upcoming_messages, overdue_messages)
        """
        upcoming_messages = []
        overdue_messages = []
        
        # Get upcoming bills (within advance_days)
        upcoming_bills = get_upcoming_bills(self.advance_days)
        
        for bill_instance in upcoming_bills:
            days_until = (bill_instance.due_date - date.today()).days
            if days_until <= self.advance_days:
                bill = bill_instance.bill
                if days_until == 0:
                    message = f"{bill.payee} payment of ${bill.expected_amount:.2f} is due TODAY"
                elif days_until == 1:
                    message = f"{bill.payee} payment of ${bill.expected_amount:.2f} is due TOMORROW"
                else:
                    message = f"{bill.payee} payment of ${bill.expected_amount:.2f} is due in {days_until} days"
                
                upcoming_messages.append(message)
        
        # Get overdue bills
        overdue_bills = get_overdue_bills()
        
        for bill_instance in overdue_bills:
            days_overdue = (date.today() - bill_instance.due_date).days
            bill = bill_instance.bill
            message = f"OVERDUE: {bill.payee} payment of ${bill.expected_amount:.2f} was due {days_overdue} days ago"
            overdue_messages.append(message)
        
        return upcoming_messages, overdue_messages
    
    def check_and_notify(self, page: Optional[ft.Page] = None):
        """Check for bills needing notification and send alerts"""
        upcoming_messages, overdue_messages = self.get_notification_messages()
        
        # Show system notifications
        if overdue_messages:
            self.show_system_notification(
                "Overdue Bills",
                f"You have {len(overdue_messages)} overdue bill payment(s)"
            )
        
        if upcoming_messages:
            self.show_system_notification(
                "Upcoming Bills", 
                f"You have {len(upcoming_messages)} bill payment(s) due soon"
            )
        
        # Show in-app notifications if page is available
        if page:
            if overdue_messages:
                combined_overdue = "\\n\\n".join(overdue_messages)
                self.show_in_app_alert(
                    page,
                    "Overdue Bills",
                    combined_overdue
                )
            
            if upcoming_messages:
                combined_upcoming = "\\n\\n".join(upcoming_messages)
                self.show_in_app_alert(
                    page,
                    "Upcoming Bills",
                    combined_upcoming
                )
    
    def get_dashboard_summary(self) -> dict:
        """Get summary data for dashboard display"""
        upcoming_bills = get_upcoming_bills(30)  # Next 30 days
        overdue_bills = get_overdue_bills()
        
        # Calculate totals
        upcoming_total = sum(bill.bill.expected_amount for bill in upcoming_bills)
        overdue_total = sum(bill.bill.expected_amount for bill in overdue_bills)
        
        # Get bills due today
        today_bills = [bill for bill in upcoming_bills if bill.due_date == date.today()]
        
        return {
            'upcoming_count': len(upcoming_bills),
            'upcoming_total': upcoming_total,
            'overdue_count': len(overdue_bills),
            'overdue_total': overdue_total,
            'today_count': len(today_bills),
            'today_bills': today_bills
        }
    
    def mark_bill_paid(self, bill_instance_id: int, transaction_id: Optional[int] = None, actual_amount: Optional[float] = None):
        """Mark a bill instance as paid"""
        bill_instance = session.query(BillInstance).get(bill_instance_id)
        if not bill_instance:
            return False
        
        bill_instance.status = 'paid'
        if transaction_id:
            bill_instance.transaction_id = transaction_id
        if actual_amount:
            bill_instance.actual_amount = actual_amount
        
        session.commit()
        return True
    
    def start_background_checker(self, page: Optional[ft.Page] = None):
        """Start background thread to periodically check for notifications"""
        def background_check():
            while self.notification_enabled:
                try:
                    self.check_and_notify(page)
                    # Check every 6 hours (21600 seconds)
                    time.sleep(21600)
                except Exception as e:
                    print(f"Error in background notification check: {e}")
                    time.sleep(3600)  # Wait 1 hour on error
        
        thread = threading.Thread(target=background_check, daemon=True)
        thread.start()
    
    def stop_notifications(self):
        """Stop notification service"""
        self.notification_enabled = False

# Global notification service instance  
notification_service = NotificationService()