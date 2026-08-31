from flask import Blueprint, redirect, url_for

from app.controllers.receptionist import ReceptionistController
from app.auth import login_required, receptionist_required


class ReceptionistRoutes:
    def __init__(self):
        self.bp = Blueprint("receptionist", __name__)
        self.controller = ReceptionistController()

    def register(self):
        self.bp.route("", methods=["GET"], endpoint="root")(
            receptionist_required(lambda: redirect(url_for("receptionist.dashboard")))
        )
        self.bp.route("/", methods=["GET"], endpoint="home")(
            receptionist_required(lambda: redirect(url_for("receptionist.dashboard")))
        )

        # ── Receptionist Dashboard ──────────────────────────
        self.bp.route("/dashboard", methods=["GET"])(
            receptionist_required(self.controller.dashboard)
        )

        # ── Order Management ────────────────────────────────
        self.bp.route("/orders", methods=["GET"])(
            receptionist_required(self.controller.orders)
        )


        # ── Finished Order History ───────────────────────────
        self.bp.route("/history", methods=["GET"])(
            receptionist_required(self.controller.history)
        )

        # ── View Single Order ────────────────────────────────
        self.bp.route("/order/<int:order_id>", methods=["GET"])(
            receptionist_required(self.controller.view_order)
        )

        # ── Mark Order As Preparing ──────────────────────────
        self.bp.route(
            "/order/<int:order_id>/preparing",
            methods=["POST"]
        )(
            receptionist_required(self.controller.mark_preparing)
        )

        # ── Mark Order As Ready ──────────────────────────────
        self.bp.route(
            "/order/<int:order_id>/ready",
            methods=["POST"]
        )(
            receptionist_required(self.controller.mark_ready)
        )

        # ── Mark Order As Served ────────────────────────────
        self.bp.route(
            "/order/<int:order_id>/served",
            methods=["POST"]
        )(
            receptionist_required(self.controller.mark_served)
        )

        # ── Clear Table ─────────────────────────────────────
        self.bp.route("/table/<int:table_id>/clear", methods=["POST"])(
            receptionist_required(self.controller.clear_table)
        )

        # ── Cancel Order ────────────────────────────────────
        self.bp.route(
            "/order/<int:order_id>/cancel",
            methods=["POST"]
        )(
            receptionist_required(self.controller.cancel_order)
        )

        # ── Order Notes ──────────────────────────────────────
        self.bp.route(
            "/order/<int:order_id>/note",
            methods=["POST"]
        )(
            receptionist_required(self.controller.save_order_note)
        )

        # ── Order Payment ────────────────────────────────────
        self.bp.route(
            "/order/<int:order_id>/settle",
            methods=["POST"]
        )(
            receptionist_required(self.controller.settle_order)
        )

        # ── Notifications ───────────────────────────────────
        self.bp.route("/notifications", methods=["GET"])(
            receptionist_required(self.controller.notifications)
        )

        # ── Live order feed for no-reload queue updates ──────
        self.bp.route("/orders/live", methods=["GET"])(
            receptionist_required(self.controller.live_orders)
        )

        return self.bp