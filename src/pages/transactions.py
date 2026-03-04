import flet as ft
from datetime import datetime, date, timedelta
from services.db import session, Transaction, Category, Bill, BillInstance
from services.label import suggest_payee
from services.notifications import notification_service
from pages.csv_import import csv_import_page

def get_transactions(limit=100):
    return session.query(Transaction).order_by(Transaction.date.desc()).limit(limit).all()

def get_categories():
    return session.query(Category).all()

def find_matching_bill_instance(transaction):
    """Find potential bill instance matches for a transaction"""
    if transaction.amount >= 0:  # Only match negative amounts (debits)
        return None
    
    amount = abs(transaction.amount)
    transaction_date = transaction.date
    
    # Look for bill instances due within ±5 days of transaction date
    start_date = transaction_date - timedelta(days=5)
    end_date = transaction_date + timedelta(days=5)
    
    potential_matches = session.query(BillInstance).join(Bill).filter(
        BillInstance.due_date.between(start_date, end_date),
        BillInstance.status == 'pending',
        Bill.is_active == True,
        # Amount within ±15% tolerance
        Bill.expected_amount.between(amount * 0.85, amount * 1.15)
    ).all()
    
    # Further filter by payee similarity if available
    if transaction.payee:
        for bill_instance in potential_matches:
            if transaction.payee.lower() in bill_instance.bill.payee.lower() or \
               bill_instance.bill.payee.lower() in transaction.payee.lower():
                return bill_instance
    
    # Return best match by date proximity
    if potential_matches:
        potential_matches.sort(key=lambda bi: abs((bi.due_date - transaction_date).days))
        return potential_matches[0]
    
    return None

def link_transaction_to_bill(transaction_id, bill_instance_id):
    """Link a transaction to a bill instance as payment"""
    try:
        transaction = session.query(Transaction).get(transaction_id)
        bill_instance = session.query(BillInstance).get(bill_instance_id)
        
        if not transaction or not bill_instance:
            return False
        
        # Update bill instance
        bill_instance.transaction_id = transaction_id
        bill_instance.actual_amount = abs(transaction.amount)
        bill_instance.status = 'paid'
        
        session.commit()
        return True
        
    except Exception:
        session.rollback()
        return False

def transactions_tab(page: ft.Page):
    def refresh_transactions():
        try:
            transactions = get_transactions()
            data_table.rows.clear()
            
            for t in transactions:
                # Handle null category
                category_name = ""
                if t.category_id:
                    category = session.query(Category).get(t.category_id)
                    category_name = category.name if category else "Unknown"
                
                                
                # Handle null payee
                if t.payee:
                    payee_name = t.payee
                elif t.label:
                    payee_name = suggest_payee(t.label) or ""
                else:
                    payee_name = ""
                
                # Check for bill matching
                matching_bill = find_matching_bill_instance(t)
                bill_suggestion = ""
                action_button = ft.Text("")
                
                if matching_bill:
                    bill_suggestion = f"Matches: {matching_bill.bill.payee}"
                    # Create a proper closure for the lambda
                    def create_link_handler(transaction_id, bill_instance_id):
                        return lambda e: link_bill_payment(transaction_id, bill_instance_id)
                    
                    action_button = ft.IconButton(
                        icon=ft.Icons.LINK,
                        tooltip=f"Link to {matching_bill.bill.payee} bill",
                        icon_color="blue", 
                        on_click=create_link_handler(t.id, matching_bill.id)
                    )
                elif t.amount < 0:  # Only show for debits
                    # Create a proper closure for the lambda
                    def create_dialog_handler(transaction_id):
                        return lambda e: show_bill_selection_dialog(transaction_id)
                        
                    action_button = ft.IconButton(
                        icon=ft.Icons.RECEIPT_LONG,
                        tooltip="Mark as bill payment",
                        icon_color="grey",
                        on_click=create_dialog_handler(t.id)
                    )
                else:
                    action_button = ft.Container()  # Empty container for credits
                
                data_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(t.date.strftime("%Y-%m-%d"))),
                        ft.DataCell(ft.Text(t.label[:50])),  # Truncate long labels
                        ft.DataCell(ft.Text(payee_name)),
                        ft.DataCell(ft.Text(category_name)),
                        ft.DataCell(ft.Text(f"{t.debit:.2f}" if t.debit > 0 else "")),
                        ft.DataCell(ft.Text(f"{t.credit:.2f}" if t.credit > 0 else "")),
                        ft.DataCell(ft.Text(f"{t.amount:.2f}", 
                                          color="red" if t.amount < 0 else "green")),
                        ft.DataCell(ft.Text(f"{t.balance:.2f}")),
                        ft.DataCell(ft.Column([
                            ft.Text(bill_suggestion, size=10, color="blue") if bill_suggestion else ft.Container(),
                            action_button
                        ], spacing=2))
                    ])
                )
            page.update()
            
        except Exception as e:
            page.open(
                ft.SnackBar(content=ft.Text(f"Error loading transactions: {e}"))
            )
    
    def link_bill_payment(transaction_id, bill_instance_id):
        """Link transaction to bill and mark as paid"""
        try:
            success = link_transaction_to_bill(transaction_id, bill_instance_id)
            if success:
                page.open(ft.SnackBar(content=ft.Text("Transaction linked to bill payment")))
                refresh_transactions()
                return True
            else:
                page.open(ft.SnackBar(content=ft.Text("Failed to link transaction to bill")))
                return False
        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error linking transaction: {str(e)}")))
            return False
    
    def show_bill_selection_dialog(transaction_id):
        """Show dialog to manually select which bill this transaction pays"""
        try:
            print(f"show_bill_selection_dialog called with transaction_id: {transaction_id}")  # Debug line
            transaction = session.query(Transaction).get(transaction_id)
            if not transaction:
                print("Transaction not found!")  # Debug line
                return
            
            # Get pending bill instances from the last 30 days to next 7 days
            start_date = transaction.date - timedelta(days=30)
            end_date = transaction.date + timedelta(days=7)
            
            pending_bills = session.query(BillInstance).join(Bill).filter(
                BillInstance.due_date.between(start_date, end_date),
                BillInstance.status == 'pending',
                Bill.is_active == True
            ).order_by(BillInstance.due_date).all()
            
            if not pending_bills:
                page.open(ft.SnackBar(content=ft.Text("No pending bills found for this time period")))
                return
            
            # Create dropdown options
            bill_options = []
            for bill_instance in pending_bills:
                bill = bill_instance.bill
                days_diff = (bill_instance.due_date - transaction.date).days
                label = f"{bill.payee} - ${bill.expected_amount:.2f} (Due: {bill_instance.due_date.strftime('%m/%d/%Y')}) [ID: {bill_instance.id}]"
                bill_options.append(ft.dropdown.Option(key=str(bill_instance.id), text=label))
            
            if not bill_options:
                page.open(ft.SnackBar(content=ft.Text("No bill options available")))
                return
            
            bill_dropdown = ft.Dropdown(
                label="Select Bill",
                options=bill_options,
                width=400
            )
            
            def confirm_bill_link(e):
                try:
                    print("confirm_bill_link called!")  # Debug line
                    if not bill_dropdown.value:
                        page.open(ft.SnackBar(content=ft.Text("Please select a bill")))
                        return
                        
                    success = link_bill_payment(transaction_id, int(bill_dropdown.value))
                    if success:
                        page.close(bill_dialog)
                    else:
                        page.open(ft.SnackBar(content=ft.Text("Failed to link transaction to bill")))
                        
                except Exception as ex:
                    page.open(ft.SnackBar(content=ft.Text(f"Error linking bill: {str(ex)}")))
                    print(f"Exception in confirm_bill_link: {ex}")  # Debug line
            
            def close_bill_dialog(e):
                page.close(bill_dialog)
            
            bill_dialog = ft.AlertDialog(
                title=ft.Text("Link Transaction to Bill"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Transaction: {transaction.label[:50]}"),
                        ft.Text(f"Amount: ${abs(transaction.amount):.2f}"),
                        ft.Text(f"Date: {transaction.date}"),
                        ft.Divider(),
                        bill_dropdown
                    ], tight=True),
                    width=500,
                    height=250
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=close_bill_dialog),
                    ft.TextButton("Link Bill", on_click=confirm_bill_link)
                ]
            )
            
            print("Setting bill dialog...")  # Debug line
            # Use page.open() method instead
            page.open(bill_dialog)
            print("Bill dialog opened with page.open()!")  # Debug line
            
        except Exception as e:
            print(f"Exception in show_bill_selection_dialog: {e}")  # Debug line
            page.open(ft.SnackBar(content=ft.Text(f"Error opening dialog: {str(e)}")))

    # Create import section
    import_section = csv_import_page(page)
    
    refresh_button = ft.ElevatedButton(
        "Refresh",
        icon=ft.Icons.REFRESH,
        on_click=lambda _: refresh_transactions()
    )

    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Date")),
            ft.DataColumn(ft.Text("Label")),
            ft.DataColumn(ft.Text("Payee")),
            ft.DataColumn(ft.Text("Category")),
            ft.DataColumn(ft.Text("Debit")),
            ft.DataColumn(ft.Text("Credit")),
            ft.DataColumn(ft.Text("Amount")),
            ft.DataColumn(ft.Text("Balance")),
            ft.DataColumn(ft.Text("Bill Actions")),
        ],
        width=1400  # Increased width for new column
    )
    
    # Initial load
    refresh_transactions()
    
    return ft.Column([
        ft.Text("Transaction Management", size=20, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        ft.Text("Import CSV", size=16, weight=ft.FontWeight.BOLD),
        import_section,
        ft.Divider(),
        ft.Row([
            refresh_button,
            ft.Text(f"Showing latest {len(data_table.rows)} transactions")
        ]),
        ft.ListView(
            controls=[data_table],
            height=400,
            width=1400,
            auto_scroll=True
        )
    ], scroll=ft.ScrollMode.AUTO)