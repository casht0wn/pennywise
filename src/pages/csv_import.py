import flet as ft
import csv
from datetime import datetime
from services.db import session, Transaction, Category
from services.label import suggest_payee, refresh_label_index
from theme import COLORS, cyber_button, mono_text

def add_transaction(transaction: Transaction):
    try:
        session.add(transaction)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error adding transaction: {e}")
        return False

def csv_import_page(page: ft.Page):
    status_text = ft.Text("No file selected", size=12, color=COLORS.TEXT_DIM, font_family="ShareTechMono")
    
    def on_import(e: ft.FilePickerResultEvent):
        if not e.files:
            status_text.value = "No files selected"
            page.update()
            return

        try:
            refresh_label_index()
        except Exception as refresh_error:
            print(f"Warning: could not refresh label index before import: {refresh_error}")
            
        imported_count = 0
        duplicate_count = 0
        error_count = 0
        
        for file in e.files:
            try:
                status_text.value = f"Processing {file.name}..."
                page.update()
                
                with open(file.path, 'r', encoding='utf-8') as f:
                    # Use csv.reader to handle quoted fields properly
                    csv_reader = csv.reader(f)
                    
                    for row_num, row in enumerate(csv_reader, 1):
                        try:
                            if len(row) != 5:
                                print(f"Row {row_num}: Expected 5 columns, got {len(row)}")
                                error_count += 1
                                continue
                                
                            date_str, label, debit_str, credit_str, balance_str = row
                            
                            # Parse date
                            date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            
                            # Parse amounts
                            debit = float(debit_str) if debit_str.strip() else 0.0
                            credit = float(credit_str) if credit_str.strip() else 0.0
                            balance = float(balance_str) if balance_str.strip() else 0.0
                            amount = credit - debit
                            
                            normalized_label = label.lower().strip()
                            payee = None
                            if label and label.strip():
                                try:
                                    payee = suggest_payee(label)
                                except Exception as suggestion_error:
                                    print(
                                        f"Row {row_num}: payee suggestion failed for label '{label}': {suggestion_error}"
                                    )
                            
                            # Check for duplicates
                            existing_transaction = session.query(Transaction).filter_by(
                                date=date,
                                label=label,
                                payee=payee or None,
                                debit=debit,
                                credit=credit,
                                balance=balance
                            ).first()
                            
                            if existing_transaction:
                                duplicate_count += 1
                                continue
                            
                            # Create new transaction
                            transaction = Transaction(
                                date=date,
                                label=label,
                                normalized_label=normalized_label,
                                payee=payee,
                                category_id=None,  # Will be set to None
                                debit=debit,
                                credit=credit,
                                amount=amount,
                                balance=balance
                            )
                            
                            if add_transaction(transaction):
                                imported_count += 1
                            else:
                                error_count += 1
                                
                        except Exception as row_error:
                            print(f"Error processing row {row_num}: {row_error}")
                            error_count += 1
                            continue
                            
            except Exception as file_error:
                status_text.value = f"Error reading file {file.name}: {file_error}"
                page.update()
                return
        
        # Update status
        if imported_count > 0:
            try:
                refresh_label_index()
            except Exception as refresh_error:
                print(f"Warning: could not refresh label index after import: {refresh_error}")

        has_errors = error_count > 0
        status_text.value = f"Import complete! Imported: {imported_count}, Duplicates: {duplicate_count}, Errors: {error_count}"
        status_text.color = COLORS.SECONDARY if has_errors else COLORS.SUCCESS
       
        # Show snackbar
        page.open(
            ft.SnackBar(
                content=ft.Text(f"Imported {imported_count} transactions"),
                action="OK"
            )
        )
        page.update()

    file_picker = ft.FilePicker(on_result=on_import)
    page.overlay.append(file_picker)
    
    import_button = cyber_button(
        "Select CSV File",
        icon=ft.Icons.UPLOAD_FILE,
        on_click=lambda _: file_picker.pick_files(
            allow_multiple=True,
            allowed_extensions=["csv"]
        ),
        color=COLORS.PRIMARY,
    )
    
    return ft.Column([
        import_button,
        status_text
    ])
