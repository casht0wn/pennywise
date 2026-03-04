import flet as ft
from services.db import session, Category

def get_categories():
    return session.query(Category).all()

def add_category(name: str):
    try:
        new_category = Category(name=name)
        session.add(new_category)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error adding category: {e}")
        return False

def categories_tab(page: ft.Page):
    def refresh_categories():
        try:
            categories = get_categories()
            data_table.rows.clear()
            
            for c in categories:
                data_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(c.id))),
                        ft.DataCell(ft.Text(c.name))
                    ])
                )
            page.update()
            
        except Exception as e:
            page.show_snack_bar(
                ft.SnackBar(content=ft.Text(f"Error loading categories: {e}"))
            )

    refresh_button = ft.ElevatedButton(
        "Refresh",
        icon=ft.Icons.REFRESH,
        on_click=lambda _: refresh_categories()
    )

    add_category_button = ft.ElevatedButton(
        "Add Category",
        icon=ft.Icons.ADD,
        on_click=lambda _: add_category_dialog.open()
    )

    add_category_dialog = ft.AlertDialog(
        title=ft.Text("Add Category"),
        content=ft.Column([
            ft.TextField(label="Category Name", autofocus=True),
            ft.TextField(label="Description", multiline=True)
        ]),
        actions=[
            ft.TextButton("Cancel", on_click=lambda _: add_category_dialog.close()),
            ft.TextButton("Add", on_click=lambda _: add_category(add_category_dialog.content[0].value))
        ]
    )


    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Name"))
        ],
        rows=[]
    )

    container = ft.Container(
        content=ft.Column([
            ft.Row([refresh_button, add_category_button]),
            data_table
        ]),
        padding=10
    )

    refresh_categories()
    return container