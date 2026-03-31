import flet as ft
from datetime import datetime, date, timedelta
from services.db import session, Transaction, Category, Bill, BillInstance
from services.label import suggest_payee
from services.notifications import notification_service
from services.bill_detection import (
    find_similar_transactions_for_bill,
    create_bill_with_transactions,
    normalize_payee_from_label,
)
from pages.csv_import import csv_import_page
from theme import (
    COLORS, neon_card, neon_divider, section_header, mono_text, cyber_button
)

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

        bill_instance.transaction_id = transaction_id
        bill_instance.actual_amount = abs(transaction.amount)
        bill_instance.status = 'paid'

        session.commit()
        return True

    except Exception:
        session.rollback()
        return False

def transactions_tab(page: ft.Page):
    col_label = lambda t: ft.Text(t, size=11, color=COLORS.TEXT_DIM)

    def refresh_transactions():
        try:
            transactions = get_transactions()
            data_table.rows.clear()

            # Single query: which transaction IDs are already linked to a bill instance?
            linked_info: dict = {}  # transaction_id -> bill payee name
            for inst, bill in (
                session.query(BillInstance, Bill)
                .join(Bill)
                .filter(BillInstance.transaction_id.isnot(None))
                .all()
            ):
                if inst.transaction_id:
                    linked_info[inst.transaction_id] = bill.payee

            for t in transactions:
                category_name = ""
                if t.category_id:
                    category = session.query(Category).get(t.category_id)
                    category_name = category.name if category else "Unknown"

                if t.payee:
                    payee_name = t.payee
                elif t.label:
                    payee_name = suggest_payee(t.label) or ""
                else:
                    payee_name = ""

                # Determine bill action state for this transaction
                bill_suggestion = ""
                bill_suggestion_color = COLORS.PRIMARY
                action_button = ft.Container()

                if t.id in linked_info:
                    bill_suggestion = f"✓ {linked_info[t.id]}"
                    bill_suggestion_color = COLORS.SUCCESS

                elif t.amount < 0:  # Only debits can be bill payments
                    matching_bill = find_matching_bill_instance(t)

                    def create_new_bill_handler(tid):
                        return lambda e: show_create_bill_from_transaction_dialog(tid)

                    if matching_bill:
                        bill_suggestion = f"Matches: {matching_bill.bill.payee}"

                        def create_link_handler(transaction_id, bill_instance_id):
                            return lambda e: link_bill_payment(transaction_id, bill_instance_id)

                        action_button = ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.LINK,
                                    tooltip=f"Link to '{matching_bill.bill.payee}' bill",
                                    icon_color=COLORS.PRIMARY,
                                    on_click=create_link_handler(t.id, matching_bill.id),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.REPEAT,
                                    tooltip="Create new recurring bill",
                                    icon_color=COLORS.WARNING,
                                    on_click=create_new_bill_handler(t.id),
                                ),
                            ],
                            spacing=0,
                        )
                    else:
                        def create_dialog_handler(transaction_id):
                            return lambda e: show_bill_selection_dialog(transaction_id)

                        action_button = ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.RECEIPT_LONG,
                                    tooltip="Mark as bill payment",
                                    icon_color=COLORS.TEXT_DIM,
                                    on_click=create_dialog_handler(t.id),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.REPEAT,
                                    tooltip="Create new recurring bill",
                                    icon_color=COLORS.WARNING,
                                    on_click=create_new_bill_handler(t.id),
                                ),
                            ],
                            spacing=0,
                        )

                amount_color = COLORS.SECONDARY if t.amount < 0 else COLORS.SUCCESS

                data_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(mono_text(t.date.strftime("%Y-%m-%d"), color=COLORS.TEXT_DIM, size=12)),
                        ft.DataCell(ft.Text(t.label[:50], color=COLORS.TEXT_PRIMARY, size=12)),
                        ft.DataCell(ft.Text(payee_name, color=COLORS.TEXT_PRIMARY, size=12)),
                        ft.DataCell(ft.Text(category_name, color=COLORS.TEXT_DIM, size=12)),
                        ft.DataCell(mono_text(f"{t.debit:.2f}" if t.debit > 0 else "", color=COLORS.SECONDARY, size=12)),
                        ft.DataCell(mono_text(f"{t.credit:.2f}" if t.credit > 0 else "", color=COLORS.SUCCESS, size=12)),
                        ft.DataCell(mono_text(f"{t.amount:.2f}", color=amount_color, size=12)),
                        ft.DataCell(mono_text(f"{t.balance:.2f}", color=COLORS.TEXT_DIM, size=12)),
                        ft.DataCell(ft.Column([
                            ft.Text(bill_suggestion, size=10, color=bill_suggestion_color, font_family="ShareTechMono") if bill_suggestion else ft.Container(),
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
            print(f"show_bill_selection_dialog called with transaction_id: {transaction_id}")
            transaction = session.query(Transaction).get(transaction_id)
            if not transaction:
                print("Transaction not found!")
                return

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

            bill_options = []
            for bill_instance in pending_bills:
                bill = bill_instance.bill
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
                    print("confirm_bill_link called!")
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
                    print(f"Exception in confirm_bill_link: {ex}")

            def close_bill_dialog(e):
                page.close(bill_dialog)

            bill_dialog = ft.AlertDialog(
                title=ft.Text("Link Transaction to Bill", color=COLORS.PRIMARY),
                bgcolor=COLORS.SURFACE_VARIANT,
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Transaction: {transaction.label[:50]}", color=COLORS.TEXT_PRIMARY, size=12),
                        mono_text(f"Amount: ${abs(transaction.amount):.2f}", color=COLORS.SECONDARY),
                        mono_text(f"Date: {transaction.date}", color=COLORS.TEXT_DIM, size=12),
                        neon_divider(COLORS.BORDER_DIM),
                        bill_dropdown
                    ], tight=True),
                    width=500,
                    height=260
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=close_bill_dialog),
                    ft.TextButton("Link Bill", on_click=confirm_bill_link, style=ft.ButtonStyle(color=COLORS.PRIMARY))
                ]
            )

            print("Setting bill dialog...")
            page.open(bill_dialog)
            print("Bill dialog opened with page.open()!")

        except Exception as e:
            print(f"Exception in show_bill_selection_dialog: {e}")
            page.open(ft.SnackBar(content=ft.Text(f"Error opening dialog: {str(e)}")))

    def show_create_bill_from_transaction_dialog(transaction_id):
        """Open a dialog to create a new recurring bill from a payment transaction.

        The selected transaction acts as a template: similar historical payments are
        scanned and presented as a checkbox list for the user to confirm before the
        bill is created and all selected transactions are linked as past payments.
        """
        try:
            transaction = session.query(Transaction).get(transaction_id)
            if not transaction:
                page.open(ft.SnackBar(content=ft.Text("Transaction not found")))
                return

            template_amount = abs(transaction.amount)
            template_payee = transaction.payee or normalize_payee_from_label(transaction.label)

            similar = find_similar_transactions_for_bill(transaction_id)

            all_dates = [transaction.date] + [t.date for t, _ in similar]
            suggested_due_day = int(round(sum(d.day for d in all_dates) / len(all_dates)))

            payee_field = ft.TextField(label="Payee / Bill Name", value=template_payee, width=320)
            amount_field = ft.TextField(
                label="Expected Amount", value=f"{template_amount:.2f}", width=150
            )
            due_day_field = ft.TextField(
                label="Due Day (1-31)", value=str(suggested_due_day), width=130
            )
            categories = get_categories()
            category_dropdown = ft.Dropdown(
                label="Category",
                options=[ft.dropdown.Option(key=str(cat.id), text=cat.name) for cat in categories],
                value=str(transaction.category_id) if transaction.category_id else None,
                width=200,
            )

            all_items = [(transaction, 1.0)] + similar
            checkbox_refs = []

            checkbox_rows = []
            for t, score in all_items:
                is_template = t.id == transaction_id
                cb = ft.Checkbox(value=True)
                checkbox_refs.append((t, cb))
                label_text = "(this payment)" if is_template else f"{score:.0%} match"
                label_color = COLORS.PRIMARY if is_template else COLORS.TEXT_DIM
                checkbox_rows.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                cb,
                                mono_text(t.date.strftime("%Y-%m-%d"), color=COLORS.TEXT_DIM, size=12),
                                ft.Text(t.label[:42], width=290, size=12, color=COLORS.TEXT_PRIMARY),
                                mono_text(f"${abs(t.amount):.2f}", color=COLORS.TEXT_PRIMARY, size=12),
                                ft.Text(label_text, size=11, color=label_color),
                            ],
                            spacing=4,
                        ),
                        border=ft.border.only(left=ft.BorderSide(3, COLORS.PRIMARY)) if is_template else None,
                        padding=ft.padding.symmetric(vertical=2, horizontal=4),
                    )
                )

            similar_section = ft.Column(
                [
                    ft.Text(
                        f"Payments to include ({len(checkbox_rows)} found — uncheck to exclude):",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS.TEXT_PRIMARY,
                    ),
                    ft.Container(
                        content=ft.Column(
                            checkbox_rows,
                            scroll=ft.ScrollMode.AUTO,
                            spacing=0,
                        ),
                        height=220,
                        border=ft.border.all(1, COLORS.BORDER_DIM),
                        border_radius=4,
                        padding=4,
                        bgcolor=COLORS.SURFACE,
                    ),
                ],
                spacing=6,
            )

            def create_bill_action(e):
                try:
                    if not payee_field.value or not payee_field.value.strip():
                        page.open(ft.SnackBar(content=ft.Text("Payee name is required")))
                        return
                    try:
                        amount = float(amount_field.value)
                        if amount <= 0:
                            raise ValueError
                    except ValueError:
                        page.open(ft.SnackBar(content=ft.Text("Enter a valid amount greater than 0")))
                        return
                    try:
                        due_day = int(due_day_field.value)
                        if not (1 <= due_day <= 31):
                            raise ValueError
                    except ValueError:
                        page.open(ft.SnackBar(content=ft.Text("Due day must be a number between 1 and 31")))
                        return

                    cat_id = int(category_dropdown.value) if category_dropdown.value else None
                    selected = [t for t, cb in checkbox_refs if cb.value]

                    if not selected:
                        page.open(ft.SnackBar(content=ft.Text("Select at least one payment to link")))
                        return

                    bill = create_bill_with_transactions(
                        payee=payee_field.value.strip(),
                        expected_amount=amount,
                        due_day=due_day,
                        category_id=cat_id,
                        transactions=selected,
                    )

                    page.open(
                        ft.SnackBar(
                            content=ft.Text(
                                f"Created bill '{bill.payee}' and linked {len(selected)} payment(s)"
                            )
                        )
                    )
                    page.close(create_bill_dialog)
                    refresh_transactions()

                except Exception as ex:
                    page.open(ft.SnackBar(content=ft.Text(f"Error creating bill: {str(ex)}")))

            create_bill_dialog = ft.AlertDialog(
                title=ft.Text("Create Recurring Bill from Payment", color=COLORS.PRIMARY),
                bgcolor=COLORS.SURFACE_VARIANT,
                content=ft.Container(
                    content=ft.Column(
                        [
                            # Template info banner
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("Template Payment", size=12, weight=ft.FontWeight.BOLD, color=COLORS.PRIMARY),
                                        ft.Text(f"Label: {transaction.label[:65]}", size=11, color=COLORS.TEXT_PRIMARY),
                                        mono_text(
                                            f"Amount: ${template_amount:.2f}   "
                                            f"Date: {transaction.date.strftime('%Y-%m-%d')}",
                                            color=COLORS.TEXT_DIM,
                                            size=11,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                                border=ft.border.only(left=ft.BorderSide(3, COLORS.PRIMARY)),
                                padding=ft.padding.only(left=10, top=6, bottom=6),
                                bgcolor=COLORS.SURFACE,
                                border_radius=ft.border_radius.only(top_right=4, bottom_right=4),
                            ),
                            neon_divider(COLORS.BORDER_DIM),
                            ft.Text("Bill Details", size=12, weight=ft.FontWeight.BOLD, color=COLORS.TEXT_PRIMARY),
                            payee_field,
                            ft.Row([amount_field, due_day_field, category_dropdown], spacing=8),
                            neon_divider(COLORS.BORDER_DIM),
                            similar_section,
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    width=720,
                    height=500,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: page.close(create_bill_dialog)),
                    ft.TextButton(
                        "Create Bill",
                        on_click=create_bill_action,
                        style=ft.ButtonStyle(color=COLORS.PRIMARY),
                    ),
                ],
            )

            page.open(create_bill_dialog)

        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error opening dialog: {str(e)}")))

    # Import section
    import_section = csv_import_page(page)

    refresh_button = cyber_button("Refresh", icon=ft.Icons.REFRESH, on_click=lambda _: refresh_transactions(), color=COLORS.TEXT_DIM)

    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(col_label("DATE")),
            ft.DataColumn(col_label("LABEL")),
            ft.DataColumn(col_label("PAYEE")),
            ft.DataColumn(col_label("CATEGORY")),
            ft.DataColumn(col_label("DEBIT")),
            ft.DataColumn(col_label("CREDIT")),
            ft.DataColumn(col_label("AMOUNT")),
            ft.DataColumn(col_label("BALANCE")),
            ft.DataColumn(col_label("BILL ACTIONS")),
        ],
        width=1400,
        heading_row_color=COLORS.SURFACE_VARIANT,
        data_row_color={ft.ControlState.HOVERED: f"{COLORS.PRIMARY}11"},
    )

    # Initial load
    refresh_transactions()

    return ft.Column([
        section_header("Transactions"),
        neon_divider(),
        section_header("Import CSV", color=COLORS.WARNING),
        neon_card(import_section, accent=COLORS.BORDER_DIM),
        neon_divider(COLORS.BORDER_DIM),
        ft.Row([
            refresh_button,
            ft.Text(f"Showing latest {len(data_table.rows)} transactions", size=12, color=COLORS.TEXT_DIM, font_family="ShareTechMono")
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        neon_card(
            ft.ListView(controls=[data_table], height=400, width=1400, auto_scroll=True),
            accent=COLORS.PRIMARY,
            padding=0,
        ),
    ], scroll=ft.ScrollMode.AUTO, spacing=12)
