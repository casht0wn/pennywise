import flet as ft
from services.db import session, Category
from theme import (
    COLORS, neon_card, neon_divider, section_header, mono_text, cyber_button
)


def categories_tab(page: ft.Page):
    col_label = lambda t: ft.Text(t, size=11, color=COLORS.TEXT_DIM)

    def refresh_categories():
        try:
            categories = session.query(Category).all()
            data_table.rows.clear()
            for i, c in enumerate(categories, 1):
                def create_edit_handler(cat_id):
                    return lambda e: show_edit_dialog(cat_id)

                data_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(mono_text(str(i), color=COLORS.TEXT_DIM, size=12)),
                        ft.DataCell(ft.Text(c.name, color=COLORS.TEXT_PRIMARY, size=13)),
                        ft.DataCell(ft.IconButton(
                            icon=ft.Icons.EDIT,
                            tooltip="Edit category name",
                            icon_color=COLORS.PRIMARY,
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
            title=ft.Text("Add Category", color=COLORS.PRIMARY),
            bgcolor=COLORS.SURFACE_VARIANT,
            content=ft.Container(content=name_field, padding=ft.padding.only(top=8)),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(dialog)),
                ft.TextButton("Add", on_click=save, style=ft.ButtonStyle(color=COLORS.PRIMARY)),
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
            title=ft.Text("Edit Category", color=COLORS.PRIMARY),
            bgcolor=COLORS.SURFACE_VARIANT,
            content=ft.Container(content=name_field, padding=ft.padding.only(top=8)),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(dialog)),
                ft.TextButton("Save", on_click=save, style=ft.ButtonStyle(color=COLORS.PRIMARY)),
            ],
        )
        page.open(dialog)

    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(col_label("#")),
            ft.DataColumn(col_label("NAME")),
            ft.DataColumn(col_label("ACTIONS")),
        ],
        rows=[],
        column_spacing=40,
        heading_row_color=COLORS.SURFACE_VARIANT,
        data_row_color={ft.ControlState.HOVERED: f"{COLORS.PRIMARY}11"},
    )

    refresh_categories()

    return ft.Column(
        [
            section_header("Categories"),
            neon_divider(),
            ft.Row([
                cyber_button("Refresh", icon=ft.Icons.REFRESH, on_click=lambda _: refresh_categories(), color=COLORS.TEXT_DIM),
                cyber_button("Add Category", icon=ft.Icons.ADD, on_click=lambda _: show_add_dialog()),
            ], spacing=8),
            neon_card(
                ft.ListView(controls=[data_table], height=400, auto_scroll=True),
                accent=COLORS.PRIMARY,
                padding=0,
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
    )
