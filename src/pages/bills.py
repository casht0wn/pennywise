"""
Bill Management Page

Allows users to:
- Review auto-detected bill suggestions
- Approve, edit, or reject suggested bills
- Manually create new bills
- View and manage existing active bills
- See upcoming bill instances and payment status
"""

import flet as ft
from datetime import datetime, date
from services.db import session, Bill, BillInstance, Category
from services.bill_detection import detect_potential_bills, create_bill_from_suggestion, BillSuggestion
from services.notifications import notification_service
from theme import (
    COLORS, neon_card, neon_divider, section_header, mono_text, cyber_button
)

def get_active_bills():
    """Get all active bills"""
    return session.query(Bill).filter_by(is_active=True).order_by(Bill.payee).all()

def get_categories():
    """Get all categories for dropdown"""
    return session.query(Category).all()

def bills_tab(page: ft.Page):
    """Main bills management tab"""

    # State variables
    current_suggestions = []

    def refresh_suggestions():
        """Scan for new bill suggestions"""
        try:
            nonlocal current_suggestions
            current_suggestions = detect_potential_bills()

            suggestions_table.rows.clear()

            for i, suggestion in enumerate(current_suggestions):
                if suggestion.confidence > 0.8:
                    confidence_color = COLORS.SUCCESS
                elif suggestion.confidence > 0.5:
                    confidence_color = COLORS.WARNING
                else:
                    confidence_color = COLORS.SECONDARY

                suggestions_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(suggestion.payee, color=COLORS.TEXT_PRIMARY, size=13)),
                        ft.DataCell(mono_text(f"${suggestion.expected_amount:.2f}", color=COLORS.TEXT_PRIMARY)),
                        ft.DataCell(mono_text(f"{suggestion.due_day}", color=COLORS.TEXT_DIM)),
                        ft.DataCell(ft.Text(suggestion.frequency.capitalize(), color=COLORS.TEXT_DIM, size=12)),
                        ft.DataCell(mono_text(f"{suggestion.confidence:.0%}", color=confidence_color)),
                        ft.DataCell(mono_text(f"{len(suggestion.supporting_transactions)}", color=COLORS.TEXT_DIM)),
                        ft.DataCell(ft.Row([
                            ft.IconButton(
                                icon=ft.Icons.CHECK_CIRCLE,
                                tooltip="Approve Bill",
                                icon_color=COLORS.SUCCESS,
                                on_click=(lambda e, idx=i: approve_suggestion(idx))
                            ),
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                tooltip="Edit & Approve",
                                icon_color=COLORS.PRIMARY,
                                on_click=(lambda e, idx=i: edit_suggestion(idx))
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CANCEL,
                                tooltip="Reject",
                                icon_color=COLORS.SECONDARY,
                                on_click=(lambda e, idx=i: reject_suggestion(idx))
                            )
                        ]))
                    ])
                )

            suggestions_status.value = f"Found {len(current_suggestions)} potential bills"
            page.update()

        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error detecting bills: {e}")))

    def approve_suggestion(index):
        """Approve a bill suggestion and create the bill"""
        try:
            suggestion = current_suggestions[index]
            new_bill = create_bill_from_suggestion(suggestion)

            page.open(ft.SnackBar(content=ft.Text(f"Created bill for {new_bill.payee}")))

            current_suggestions.pop(index)
            refresh_suggestions()
            refresh_bills()

        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error creating bill: {e}")))

    def edit_suggestion(index):
        """Open edit dialog for a suggestion"""
        suggestion = current_suggestions[index]

        payee_field = ft.TextField(label="Payee", value=suggestion.payee)
        amount_field = ft.TextField(label="Expected Amount", value=str(suggestion.expected_amount))
        due_day_field = ft.TextField(label="Due Day (1-31)", value=str(suggestion.due_day))

        categories = get_categories()
        category_dropdown = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option(key=cat.id, text=cat.name) for cat in categories],
            value=suggestion.category_id
        )

        def save_edited_bill(e):
            try:
                if not payee_field.value or not payee_field.value.strip():
                    page.open(ft.SnackBar(content=ft.Text("Payee name is required")))
                    return

                if not amount_field.value or float(amount_field.value) <= 0:
                    page.open(ft.SnackBar(content=ft.Text("Valid amount is required")))
                    return

                due_day = int(due_day_field.value)
                if due_day < 1 or due_day > 31:
                    page.open(ft.SnackBar(content=ft.Text("Due day must be between 1 and 31")))
                    return

                edited_suggestion = BillSuggestion(
                    payee=payee_field.value.strip(),
                    expected_amount=float(amount_field.value),
                    due_day=due_day,
                    frequency=suggestion.frequency,
                    confidence=suggestion.confidence,
                    supporting_transactions=suggestion.supporting_transactions,
                    category_id=int(category_dropdown.value) if category_dropdown.value else None
                )

                new_bill = create_bill_from_suggestion(edited_suggestion)
                page.open(ft.SnackBar(content=ft.Text(f"Created edited bill for {new_bill.payee}")))

                page.close(edit_dialog)

                current_suggestions.pop(index)
                refresh_suggestions()
                refresh_bills()

            except ValueError as ve:
                page.open(ft.SnackBar(content=ft.Text(f"Invalid input: {ve}")))
            except Exception as ex:
                page.open(ft.SnackBar(content=ft.Text(f"Error saving bill: {ex}")))

        edit_dialog = ft.AlertDialog(
            title=ft.Text("Edit Bill Suggestion", color=COLORS.PRIMARY),
            bgcolor=COLORS.SURFACE_VARIANT,
            content=ft.Container(
                content=ft.Column([
                    payee_field,
                    amount_field,
                    due_day_field,
                    category_dropdown
                ], tight=True),
                width=400,
                height=300
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(edit_dialog)),
                ft.TextButton("Save Bill", on_click=save_edited_bill, style=ft.ButtonStyle(color=COLORS.PRIMARY))
            ]
        )

        page.open(edit_dialog)

    def reject_suggestion(index):
        """Reject a bill suggestion"""
        suggestion = current_suggestions[index]
        current_suggestions.pop(index)
        refresh_suggestions()
        page.open(ft.SnackBar(content=ft.Text(f"Rejected suggestion for {suggestion.payee}")))

    def refresh_bills():
        """Refresh the active bills table"""
        try:
            bills = get_active_bills()
            bills_table.rows.clear()

            for bill in bills:
                next_instance = session.query(BillInstance).filter_by(
                    bill_id=bill.id, status='pending'
                ).filter(BillInstance.due_date >= date.today()).order_by(BillInstance.due_date).first()

                next_due = next_instance.due_date.strftime("%Y-%m-%d") if next_instance else "No upcoming"

                category_name = ""
                if bill.category_id:
                    category = session.query(Category).get(bill.category_id)
                    category_name = category.name if category else ""

                bills_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(bill.payee, color=COLORS.TEXT_PRIMARY, size=13)),
                        ft.DataCell(mono_text(f"${bill.expected_amount:.2f}", color=COLORS.TEXT_PRIMARY)),
                        ft.DataCell(mono_text(f"{bill.due_day}", color=COLORS.TEXT_DIM)),
                        ft.DataCell(ft.Text(bill.frequency.capitalize(), color=COLORS.TEXT_DIM, size=12)),
                        ft.DataCell(ft.Text(category_name, color=COLORS.TEXT_DIM, size=12)),
                        ft.DataCell(mono_text(next_due, color=COLORS.PRIMARY)),
                        ft.DataCell(ft.Row([
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                tooltip="Edit Bill",
                                icon_color=COLORS.PRIMARY,
                                on_click=(lambda e, bill_id=bill.id: edit_bill(bill_id))
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE,
                                tooltip="Deactivate Bill",
                                icon_color=COLORS.SECONDARY,
                                on_click=(lambda e, bill_id=bill.id: deactivate_bill(bill_id))
                            )
                        ]))
                    ])
                )

            bills_status.value = f"Active bills: {len(bills)}"
            page.update()

        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error loading bills: {e}")))

    def edit_bill(bill_id):
        """Edit an existing bill"""
        bill = session.query(Bill).get(bill_id)
        if not bill:
            return

        payee_field = ft.TextField(label="Payee", value=bill.payee)
        amount_field = ft.TextField(label="Expected Amount", value=str(bill.expected_amount))
        due_day_field = ft.TextField(label="Due Day (1-31)", value=str(bill.due_day))

        categories = get_categories()
        category_dropdown = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option(key=cat.id, text=cat.name) for cat in categories],
            value=bill.category_id
        )

        def save_bill_changes(e):
            try:
                if not payee_field.value or not payee_field.value.strip():
                    page.open(ft.SnackBar(content=ft.Text("Payee name is required")))
                    return

                if not amount_field.value:
                    page.open(ft.SnackBar(content=ft.Text("Amount is required")))
                    return

                try:
                    amount = float(amount_field.value)
                    if amount <= 0:
                        page.open(ft.SnackBar(content=ft.Text("Amount must be greater than 0")))
                        return
                except ValueError:
                    page.open(ft.SnackBar(content=ft.Text("Invalid amount format")))
                    return

                try:
                    due_day = int(due_day_field.value)
                    if due_day < 1 or due_day > 31:
                        page.open(ft.SnackBar(content=ft.Text("Due day must be between 1 and 31")))
                        return
                except ValueError:
                    page.open(ft.SnackBar(content=ft.Text("Due day must be a number")))
                    return

                old_due_day = bill.due_day
                bill.payee = payee_field.value.strip()
                bill.expected_amount = amount
                bill.due_day = due_day
                bill.category_id = int(category_dropdown.value) if category_dropdown.value else None

                session.commit()

                if old_due_day != due_day:
                    print(f"Due day changed from {old_due_day} to {due_day}, regenerating instances...")
                    from datetime import date
                    today = date.today()
                    deleted_count = session.query(BillInstance).filter(
                        BillInstance.bill_id == bill.id,
                        BillInstance.due_date >= today,
                        BillInstance.status == 'pending'
                    ).delete()
                    print(f"Deleted {deleted_count} future bill instances")

                    from services.bill_detection import generate_future_bill_instances
                    generate_future_bill_instances(bill.id)
                    session.commit()
                    print(f"Generated new bill instances for due day {due_day}")

                page.open(ft.SnackBar(content=ft.Text(f"Updated bill for {bill.payee}")))

                page.close(edit_dialog)
                refresh_bills()

            except Exception as ex:
                session.rollback()
                page.open(ft.SnackBar(content=ft.Text(f"Error updating bill: {str(ex)}")))

        edit_dialog = ft.AlertDialog(
            title=ft.Text("Edit Bill", color=COLORS.PRIMARY),
            bgcolor=COLORS.SURFACE_VARIANT,
            content=ft.Container(
                content=ft.Column([
                    payee_field,
                    amount_field,
                    due_day_field,
                    category_dropdown
                ], tight=True),
                width=400,
                height=300
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(edit_dialog)),
                ft.TextButton("Save Changes", on_click=save_bill_changes, style=ft.ButtonStyle(color=COLORS.PRIMARY))
            ]
        )

        page.open(edit_dialog)

    def deactivate_bill(bill_id):
        """Deactivate a bill (soft delete)"""
        try:
            bill = session.query(Bill).get(bill_id)
            if bill:
                bill.is_active = False
                session.commit()
                page.open(ft.SnackBar(content=ft.Text(f"Deactivated bill for {bill.payee}")))
                refresh_bills()
        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error deactivating bill: {e}")))

    def close_dialog(dialog):
        """Helper to close dialog"""
        page.close(dialog)

    def show_manual_create_dialog():
        """Show dialog to manually create a bill"""
        try:
            print("show_manual_create_dialog called!")
            payee_field = ft.TextField(label="Payee")
            amount_field = ft.TextField(label="Expected Amount")
            due_day_field = ft.TextField(label="Due Day (1-31)")

            categories = get_categories()
            category_dropdown = ft.Dropdown(
                label="Category",
                options=[ft.dropdown.Option(key=cat.id, text=cat.name) for cat in categories]
            )

            def create_manual_bill(e):
                try:
                    print("create_manual_bill called!")
                    if not payee_field.value or not payee_field.value.strip():
                        page.open(ft.SnackBar(content=ft.Text("Payee name is required")))
                        return

                    if not amount_field.value:
                        page.open(ft.SnackBar(content=ft.Text("Amount is required")))
                        return

                    try:
                        amount = float(amount_field.value)
                        if amount <= 0:
                            page.open(ft.SnackBar(content=ft.Text("Amount must be greater than 0")))
                            return
                    except ValueError:
                        page.open(ft.SnackBar(content=ft.Text("Invalid amount format")))
                        return

                    if not due_day_field.value:
                        page.open(ft.SnackBar(content=ft.Text("Due day is required")))
                        return

                    try:
                        due_day = int(due_day_field.value)
                        if due_day < 1 or due_day > 31:
                            page.open(ft.SnackBar(content=ft.Text("Due day must be between 1 and 31")))
                            return
                    except ValueError:
                        page.open(ft.SnackBar(content=ft.Text("Due day must be a number")))
                        return

                    new_bill = Bill(
                        payee=payee_field.value.strip(),
                        expected_amount=amount,
                        due_day=due_day,
                        frequency='monthly',
                        category_id=int(category_dropdown.value) if category_dropdown.value else None,
                        is_active=True
                    )

                    session.add(new_bill)
                    session.commit()

                    from services.bill_detection import generate_future_bill_instances
                    generate_future_bill_instances(new_bill.id)

                    page.open(ft.SnackBar(content=ft.Text(f"Created bill for {new_bill.payee}")))

                    page.close(create_dialog)
                    refresh_bills()

                except Exception as ex:
                    session.rollback()
                    page.open(ft.SnackBar(content=ft.Text(f"Error creating bill: {str(ex)}")))
                    print(f"Exception in create_manual_bill: {ex}")

            def close_create_dialog(e):
                page.close(create_dialog)

            create_dialog = ft.AlertDialog(
                title=ft.Text("Create New Bill", color=COLORS.PRIMARY),
                bgcolor=COLORS.SURFACE_VARIANT,
                content=ft.Container(
                    content=ft.Column([
                        payee_field,
                        amount_field,
                        due_day_field,
                        category_dropdown
                    ], tight=True),
                    width=400,
                    height=300
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=close_create_dialog),
                    ft.TextButton("Create Bill", on_click=create_manual_bill, style=ft.ButtonStyle(color=COLORS.PRIMARY))
                ]
            )

            print("Setting dialog...")
            page.open(create_dialog)
            print("Dialog opened with page.open()!")

        except Exception as e:
            print(f"Exception in show_manual_create_dialog: {e}")
            page.open(ft.SnackBar(content=ft.Text(f"Error opening dialog: {str(e)}")))

    # Create UI components
    scan_button = cyber_button("Scan for Bills", icon=ft.Icons.SEARCH, on_click=lambda _: refresh_suggestions(), color=COLORS.WARNING)
    create_button = cyber_button("Create Manual Bill", icon=ft.Icons.ADD, on_click=lambda _: show_manual_create_dialog())
    refresh_bills_button = cyber_button("Refresh Bills", icon=ft.Icons.REFRESH, on_click=lambda _: refresh_bills(), color=COLORS.TEXT_DIM)

    suggestions_status = ft.Text(
        "Click 'Scan for Bills' to detect recurring payments",
        size=12,
        color=COLORS.TEXT_DIM,
        font_family="ShareTechMono",
    )
    bills_status = ft.Text("Loading bills...", size=12, color=COLORS.TEXT_DIM, font_family="ShareTechMono")

    col_label = lambda t: ft.Text(t, size=11, color=COLORS.TEXT_DIM)

    # Bill suggestions table
    suggestions_table = ft.DataTable(
        columns=[
            ft.DataColumn(col_label("PAYEE")),
            ft.DataColumn(col_label("AMOUNT")),
            ft.DataColumn(col_label("DUE DAY")),
            ft.DataColumn(col_label("FREQUENCY")),
            ft.DataColumn(col_label("CONFIDENCE")),
            ft.DataColumn(col_label("OCCURRENCES")),
            ft.DataColumn(col_label("ACTIONS")),
        ],
        width=1200,
        heading_row_color=COLORS.SURFACE_VARIANT,
        data_row_color={ft.ControlState.HOVERED: f"{COLORS.WARNING}11"},
    )

    # Active bills table
    bills_table = ft.DataTable(
        columns=[
            ft.DataColumn(col_label("PAYEE")),
            ft.DataColumn(col_label("AMOUNT")),
            ft.DataColumn(col_label("DUE DAY")),
            ft.DataColumn(col_label("FREQUENCY")),
            ft.DataColumn(col_label("CATEGORY")),
            ft.DataColumn(col_label("NEXT DUE")),
            ft.DataColumn(col_label("ACTIONS")),
        ],
        width=1200,
        heading_row_color=COLORS.SURFACE_VARIANT,
        data_row_color={ft.ControlState.HOVERED: f"{COLORS.PRIMARY}11"},
    )

    # Initial load
    refresh_bills()

    return ft.Column([
        section_header("Bills"),
        neon_divider(),

        # Bill suggestions section
        section_header("Suggested Recurring Bills", color=COLORS.WARNING),
        ft.Row([scan_button, suggestions_status], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        neon_card(
            ft.ListView(controls=[suggestions_table], height=280, auto_scroll=True),
            accent=COLORS.WARNING,
            padding=0,
        ),

        neon_divider(COLORS.BORDER_DIM),

        # Active bills section
        section_header("Active Bills"),
        ft.Row([refresh_bills_button, create_button, bills_status], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        neon_card(
            ft.ListView(controls=[bills_table], height=380, auto_scroll=True),
            accent=COLORS.PRIMARY,
            padding=0,
        ),
    ], scroll=ft.ScrollMode.AUTO, spacing=12)
