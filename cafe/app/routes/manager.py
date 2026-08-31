from flask import Blueprint, redirect, url_for

from app.controllers.manager import ManagerController
from app.auth import manager_required


class ManagerRoutes:
    def __init__(self):
        self.bp = Blueprint("manager", __name__)
        self.controller = ManagerController()

    def register(self):

        self.bp.route("", methods=["GET"], endpoint="root")(
            manager_required(lambda: redirect(url_for("manager.dashboard")))
        )
        self.bp.route("/", methods=["GET"], endpoint="home")(
            manager_required(lambda: redirect(url_for("manager.dashboard")))
        )

        # ── Manager Dashboard ────────────────────────────────
        self.bp.route("/dashboard", methods=["GET"])(
            manager_required(self.controller.dashboard)
        )

        self.bp.route("/table-qr", methods=["GET"])(
            manager_required(self.controller.table_qr_page)
        )

        self.bp.route("/qr/<int:table_id>", methods=["GET"])(
            manager_required(self.controller.table_qr)
        )
        self.bp.route("/qr/<int:table_id>/download", methods=["GET"])(
            manager_required(self.controller.download_table_qr)
        )

        # ── Menu Management ─────────────────────────────────
        self.bp.route("/menu", methods=["GET"])(
            manager_required(self.controller.menu)
        )

        # ── Inventory Management ────────────────────────────
        self.bp.route("/inventory", methods=["GET"])(
            manager_required(self.controller.inventory)
        )
        self.bp.route("/inventory/add", methods=["POST"])(
            manager_required(self.controller.add_inventory_item)
        )
        self.bp.route("/inventory/<int:item_id>/update", methods=["POST"])(
            manager_required(self.controller.update_inventory_item)
        )
        self.bp.route("/inventory/<int:item_id>/adjust", methods=["POST"])(
            manager_required(self.controller.adjust_inventory)
        )
        self.bp.route("/inventory/<int:item_id>/archive", methods=["POST"])(
            manager_required(self.controller.archive_inventory_item)
        )

        # ── Add Menu Item ───────────────────────────────────
        self.bp.route("/menu/add", methods=["GET", "POST"])(
            manager_required(self.controller.add_menu_item)
        )

        # ── Edit Menu Item ──────────────────────────────────
        self.bp.route(
            "/menu/edit/<int:item_id>",
            methods=["GET", "POST"]
        )(
            manager_required(self.controller.edit_menu_item)
        )

        # ── Delete Menu Item ─────────────────────────────────
        self.bp.route(
            "/menu/delete/<int:item_id>",
            methods=["POST"]
        )(
            manager_required(self.controller.delete_menu_item)
        )

        # ── Permanently Delete Menu Item ─────────────────────
        self.bp.route(
            "/menu/delete-permanently/<int:item_id>",
            methods=["POST"],
        )(
            manager_required(self.controller.permanently_delete_menu_item)
        )

        # ── Order History ───────────────────────────────────
        self.bp.route("/history", methods=["GET"])(
            manager_required(self.controller.history)
        )

        # ── Reports ─────────────────────────────────────────
        self.bp.route("/reports", methods=["GET"])(
            manager_required(self.controller.reports)
        )

        # ── Sales Statistics ─────────────────────────────────
        self.bp.route("/sales", methods=["GET"])(
            manager_required(self.controller.sales)
        )

        # ── Filter Reports By Date ──────────────────────────
        self.bp.route("/reports/filter", methods=["GET"])(
            manager_required(self.controller.filter_reports)
        )

        # ── View Order ──────────────────────────────────────
        self.bp.route(
            "/order/<int:order_id>",
            methods=["GET"]
        )(
            manager_required(self.controller.view_order)
        )

        return self.bp  