import flet as ft
from services.db import session, Category


def categories_tab(page: ft.Page):
    def refresh_categories():
        try:
            categories = session.query(Category).all()
            data_table.rows.clear()
            for i, c in enumerate(categories, 1):
                def create_edit_handler(cat_id):
                    return lambda e: show_edit_dialog(cat_id)

                data_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(i), color="grey")),
                        ft.DataCell(ft.Text(c.name)),
                        ft.DataCell(ft.IconButton(
                            icon=ft.Icons.EDIT,
                            tooltip="Edit category name",
                            icon_color="blue",
                            on_click=create_edit_handler(c.id),
                        )),
                    ])
                )
            page.update()
        except Exception as e:
            page.open(ft.SnackBar(content=ft.Text(f"Error loading categories: {e}")))

    def show_add_dialog():
        name_field = ft.TextField(label="Category Name", autofocus=True, width=300)

        def save(e):
            name = (name_field.value or "").strip()
            if not name:
                page.open(ft.SnackBar(content=ft.Text("Category name is required")))
                return
            try:
                session.add(Category(name=name))
                session.commit()
                page.close(dialog)
                refresh_categories()
                page.open(ft.SnackBar(content=ft.Text(f"Added category '{name}'")))
            except Exception as ex:
                session.rollback()
                page.open(ft.SnackBar(content=ft.Text(f"Error: {ex}")))

        dialog = ft.AlertDialog(
            title=ft.Text("Add Category"),
            content=ft.Container(content=name_field, padding=ft.padding.only(top=8)),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(dialog)),
                ft.ElevatedButton("Add", on_click=save),
            ],
        )
        page.open(dialog)

    def show_edit_dialog(category_id):
        category = session.query(Category).get(category_id)
        if not category:
            return

        name_field = ft.TextField(
            label="Category Name", value=category.name, autofocus=True, width=300
        )

        def save(e):
            name = (name_field.value or "").strip()
            if not name:
                page.open(ft.SnackBar(content=ft.Text("Category name is required")))
                return
            try:
                category.name = name
                session.commit()
                page.close(dialog)
                refresh_categories()
                page.open(ft.SnackBar(content=ft.Text(f"Renamed to '{name}'")))
            except Exception as ex:
                session.rollback()
                page.open(ft.SnackBar(content=ft.Text(f"Error: {ex}")))

        dialog = ft.AlertDialog(
            title=ft.Text("Edit Category"),
            content=ft.Container(content=name_field, padding=ft.padding.only(top=8)),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(dialog)),
                ft.ElevatedButton("Save", on_click=save),
            ],
        )
        page.open(dialog)

    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("#")),
            ft.DataColumn(ft.Text("Name")),
            ft.DataColumn(ft.Text("Actions")),
        ],
        rows=[],
        column_spacing=40,
    )

    refresh_categories()

    return ft.Column(
        [
            ft.Text("Categories", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton("Refresh", icon=ft.Icons.REFRESH, on_click=lambda _: refresh_categories()),
                ft.ElevatedButton("Add Category", icon=ft.Icons.ADD, on_click=lambda _: show_add_dialog()),
            ]),
            ft.ListView(controls=[data_table], height=400, auto_scroll=True),
        ],
        scroll=ft.ScrollMode.AUTO,
    )
