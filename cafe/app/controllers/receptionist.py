"""
=============================================================
  Restaurant Receptionist Controller
=============================================================

  Main responsibilities:

    - Display receptionist dashboard
    - Display incoming orders
    - View order details
    - Change order status
    - Mark orders as preparing
    - Mark orders as ready
    - Mark orders as served
    - Cancel orders
    - Clear restaurant tables
    - Provide order notifications

=============================================================
"""

from flask import render_template, redirect, url_for, flash, request, jsonify

from app.controllers.base_controllers import BaseController
from app.modules.database import Database


class ReceptionistController(BaseController):
    """
    Controller for Receptionist operations.
    """

    @staticmethod
    def _wants_json():
        return "application/json" in request.headers.get("Accept", "").lower()

    # =========================================================
    # RECEPTIONIST DASHBOARD
    # =========================================================

    def dashboard(self):
        """
        Display receptionist dashboard.

        Shows:
            - Pending orders
            - Preparing orders
            - Ready orders
            - Served orders
            - Recent orders
            - Table information
        """

        db = Database()

        try:

            # -------------------------------------------------
            # Get all orders
            # -------------------------------------------------

            orders = db.fetch_all("""
                SELECT
                    o.id,
                    o.id AS order_number,
                    o.table_id,
                    t.name AS table_name,
                    o.status,
                    o.created_at
                FROM orders o

                LEFT JOIN restaurant_tables t
                    ON o.table_id = t.id

                ORDER BY o.id DESC
            """)

            # Attach item details expected by the dashboard cards.
            for order in orders:
                order["items"] = db.fetch_all("""
                    SELECT oi.item_id, mi.name, oi.quantity, oi.price_at_order,
                           (oi.quantity * oi.price_at_order) AS subtotal
                    FROM order_items oi
                    LEFT JOIN menu_items mi ON mi.id = oi.item_id
                    WHERE oi.order_id = %s
                    ORDER BY oi.id ASC
                """, (order["id"],))
                order["total"] = sum(
                    float(item["subtotal"] or 0) for item in order["items"]
                )
                table_label = order["table_name"] or f"Table {order['table_id']}"
                order["display_title"] = (
                    f"New Order from {table_label}"
                    if order["status"] in ("Placed", "pending")
                    else f"Order #{order['id']} from {table_label}"
                )

            # -------------------------------------------------
            # Pending orders
            # -------------------------------------------------

            incoming_count = db.fetch_one("""
                SELECT COUNT(*) AS total
                FROM orders
                WHERE status IN ('Placed', 'pending')
            """)

            # -------------------------------------------------
            # Preparing orders
            # -------------------------------------------------

            preparing_count = db.fetch_one("""
                SELECT COUNT(*) AS total
                FROM orders
                WHERE status = 'preparing'
            """)

            # -------------------------------------------------
            # Ready orders
            # -------------------------------------------------

            ready_count = db.fetch_one("""
                SELECT COUNT(*) AS total
                FROM orders
                WHERE status = 'ready'
            """)

            # -------------------------------------------------
            # Served orders
            # -------------------------------------------------

            served_count = db.fetch_one("""
                SELECT COUNT(*) AS total
                FROM orders
                WHERE status = 'served'
            """)

            # -------------------------------------------------
            # Tables with current status
            # -------------------------------------------------

            tables = db.fetch_all("""
                SELECT
                    t.id,
                    t.name,
                    t.status,

                    (
                        SELECT o.id
                        FROM orders o
                        WHERE o.table_id = t.id
                        AND o.status IN (
                            'Placed',
                            'pending',
                            'preparing',
                            'ready',
                            'served'
                        )
                        ORDER BY o.id DESC
                        LIMIT 1
                    ) AS current_order_id,

                    (
                        SELECT o.status
                        FROM orders o
                        WHERE o.table_id = t.id
                        AND o.status IN (
                            'Placed',
                            'pending',
                            'preparing',
                            'ready',
                            'served'
                        )
                        ORDER BY o.id DESC
                        LIMIT 1
                    ) AS current_order_status

                FROM restaurant_tables t
                ORDER BY t.id ASC
            """)

            return render_template(
                "receptionist/dashboard.html",

                orders=orders,

                incoming_count=incoming_count["total"],
                preparing_count=preparing_count["total"],
                ready_count=ready_count["total"],
                served_count=served_count["total"],

                tables=tables
            )

        finally:
            db.close()

    # =========================================================
    # ALL ORDERS
    # =========================================================

    def orders(self):
        """Display active orders with filters and payment information."""
        selected_status = request.args.get("status", "").strip().lower()
        search_query = request.args.get("q", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()
        valid_statuses = {"pending", "preparing", "ready", "served"}

        if selected_status not in valid_statuses:
            selected_status = ""

        query = """
            SELECT
                o.id,
                COALESCE(o.order_number, o.id) AS order_number,
                o.table_id,
                t.name AS table_name,
                o.status,
                o.total_amount,
                o.receptionist_note,
                o.created_at,
                COALESCE(p.payment_status, 'unpaid') AS payment_status,
                COALESCE(p.payment_method, '') AS payment_method
            FROM orders o
            LEFT JOIN restaurant_tables t
                ON o.table_id = t.id
            LEFT JOIN payments p
                ON p.id = (
                    SELECT MAX(p2.id)
                    FROM payments p2
                    WHERE p2.order_id = o.id
                )
            WHERE o.status IN ('Placed', 'pending', 'preparing', 'ready', 'served')
        """
        params = []

        if selected_status:
            query += " AND LOWER(o.status) = %s"
            params.append(selected_status)

        if search_query:
            query += " AND (CAST(o.id AS CHAR) LIKE %s OR t.name LIKE %s)"
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern])

        if start_date:
            query += " AND DATE(o.created_at) >= %s"
            params.append(start_date)

        if end_date:
            query += " AND DATE(o.created_at) <= %s"
            params.append(end_date)

        query += " ORDER BY o.created_at DESC, o.id DESC"

        db = Database()
        try:
            orders = db.fetch_all(query, tuple(params))

            for order in orders:
                order["items"] = db.fetch_all("""
                    SELECT
                        oi.item_id,
                        mi.name,
                        oi.quantity,
                        oi.price_at_order,
                        (oi.quantity * oi.price_at_order) AS subtotal
                    FROM order_items oi
                    LEFT JOIN menu_items mi ON mi.id = oi.item_id
                    WHERE oi.order_id = %s
                    ORDER BY oi.id ASC
                """, (order["id"],))

                order["total"] = float(
                    order["total_amount"] or 0
                ) or sum(
                    float(item["subtotal"] or 0)
                    for item in order["items"]
                )

            counts = db.fetch_one("""
                SELECT
                    COUNT(*) AS all_orders,
                    SUM(status IN ('Placed', 'pending')) AS pending_orders,
                    SUM(status = 'preparing') AS preparing_orders,
                    SUM(status = 'ready') AS ready_orders,
                    SUM(status = 'served') AS served_orders
                FROM orders
                WHERE status IN ('Placed', 'pending', 'preparing', 'ready', 'served')
            """) or {}
        finally:
            db.close()

        return render_template(
            "receptionist/orders.html",
            orders=orders,
            selected_status=selected_status,
            search_query=search_query,
            start_date=start_date,
            end_date=end_date,
            order_counts={
                "all": int(counts.get("all_orders") or 0),
                "pending": int(counts.get("pending_orders") or 0),
                "preparing": int(counts.get("preparing_orders") or 0),
                "ready": int(counts.get("ready_orders") or 0),
                "served": int(counts.get("served_orders") or 0),
            },
        )

    # =========================================================
    # FINISHED ORDER HISTORY
    # =========================================================

    def history(self):
        db = Database()
        try:
            orders = db.fetch_all("""
                SELECT o.id, o.order_number, o.table_id,
                       t.name AS table_name, o.status, o.created_at,
                       o.total_amount
                FROM orders o
                LEFT JOIN restaurant_tables t ON o.table_id = t.id
                WHERE o.status IN ('served', 'cleared', 'cancelled')
                ORDER BY o.created_at DESC
                LIMIT 100
            """)
            for order in orders:
                order["items"] = db.fetch_all("""
                    SELECT mi.name, oi.quantity, oi.price_at_order,
                           (oi.quantity * oi.price_at_order) AS subtotal
                    FROM order_items oi
                    LEFT JOIN menu_items mi ON mi.id = oi.item_id
                    WHERE oi.order_id = %s
                    ORDER BY oi.id ASC
                """, (order["id"],))
        finally:
            db.close()

        import json
        history_json = json.dumps([
            {
                "id": order["id"],
                "order_number": order.get("order_number") or order["id"],
                "table_id": order.get("table_id"),
                "table_name": order.get("table_name"),
                "status": order.get("status"),
                "created_at": str(order.get("created_at") or ""),
                "total_amount": float(order.get("total_amount") or 0),
                "items": [
                    {
                        "name": item.get("name") or "Item",
                        "quantity": int(item.get("quantity") or 0),
                        "subtotal": float(item.get("subtotal") or 0)
                    }
                    for item in order.get("items", [])
                ]
            }
            for order in orders
        ])
        return render_template(
            "receptionist/history.html",
            orders=orders,
            order_history_json=history_json
        )

    # =========================================================
    # ORDER DETAILS
    # =========================================================

    def order_details(self, order_id):
        """
        Display items belonging to an order.
        """

        db = Database()

        try:

            # -------------------------------------------------
            # Get order
            # -------------------------------------------------

            order = db.fetch_one("""
                SELECT
                    o.id,
                    o.id AS order_number,
                    o.table_id,
                    t.name AS table_name,
                    o.status,
                    o.created_at

                FROM orders o

                LEFT JOIN restaurant_tables t
                    ON o.table_id = t.id

                WHERE o.id = %s
            """, (order_id,))

            if not order:

                flash(
                    "Order not found.",
                    "danger"
                )

                return redirect(
                    url_for("receptionist.orders")
                )

            # -------------------------------------------------
            # Get order items
            # -------------------------------------------------

            items = db.fetch_all("""
                SELECT
                    oi.id,
                    oi.item_id,
                    m.name AS item_name,
                    oi.quantity,
                    oi.price_at_order,

                    (
                        oi.quantity * oi.price_at_order
                    ) AS subtotal

                FROM order_items oi

                JOIN menu_items m
                    ON oi.item_id = m.id

                WHERE oi.order_id = %s

                ORDER BY oi.id ASC
            """, (order_id,))

            # -------------------------------------------------
            # Calculate total
            # -------------------------------------------------

            total = sum(
                float(item["subtotal"])
                for item in items
            )

            return render_template(
                "receptionist/orders.html",
                order=order,
                items=items,
                total=total
            )

        finally:
            db.close()

    # =========================================================
    # MARK ORDER AS PREPARING
    # =========================================================

    def mark_preparing(self, order_id):
        """
        Change pending order to preparing.
        """

        db = Database()

        try:

            order = db.fetch_one("""
                SELECT
                    id,
                    status
                FROM orders
                WHERE id = %s
            """, (order_id,))

            if not order:

                flash(
                    "Order not found.",
                    "danger"
                )

                return redirect(
                    url_for("receptionist.orders")
                )

            if order["status"] not in ("Placed", "pending"):

                flash(
                    "Only placed or pending orders can be marked as preparing.",
                    "warning"
                )

                return redirect(
                    url_for("receptionist.orders")
                )

            db.execute("""
                UPDATE orders

                SET status = 'preparing'

                WHERE id = %s
            """, (order_id,))

            message = f"Order #{order_id} is now being prepared."
            flash(message, "info")

            if self._wants_json():
                return jsonify({
                    "success": True,
                    "order_id": order_id,
                    "status": "preparing",
                    "message": message,
                })

            return redirect(
                url_for("receptionist.orders")
            )

        finally:
            db.close()

    # =========================================================
    # MARK ORDER AS READY
    # =========================================================

    def mark_ready(self, order_id):
        """
        Change preparing order to ready.
        """

        db = Database()

        try:

            order = db.fetch_one("""
                SELECT
                    id,
                    status
                FROM orders
                WHERE id = %s
            """, (order_id,))

            if not order:

                flash(
                    "Order not found.",
                    "danger"
                )

                return redirect(
                    url_for("receptionist.orders")
                )

            if order["status"] != "preparing":

                flash(
                    "Only preparing orders can be marked as ready.",
                    "warning"
                )

                return redirect(
                    url_for("receptionist.orders")
                )

            db.execute("""
                UPDATE orders

                SET status = 'ready'

                WHERE id = %s
            """, (order_id,))

            message = f"Order #{order_id} is ready."
            flash(message, "success")

            if self._wants_json():
                return jsonify({
                    "success": True,
                    "order_id": order_id,
                    "status": "ready",
                    "message": message,
                })

            return redirect(
                url_for("receptionist.orders")
            )

        finally:
            db.close()

    # =========================================================
    # MARK ORDER AS SERVED
    # =========================================================

    def mark_served(self, order_id):
        """
        Mark ready order as served.

        IMPORTANT:

        The table is NOT cleared here.

        After the order is served, the table remains occupied
        until receptionist explicitly clicks "Clear Table".
        """

        db = Database()

        try:

            order = db.fetch_one("""
                SELECT
                    id,
                    table_id,
                    status
                FROM orders
                WHERE id = %s
            """, (order_id,))

            if not order:

                flash(
                    "Order not found.",
                    "danger"
                )

                return redirect(
                    url_for("receptionist.orders")
                )

            if order["status"] != "ready":

                flash(
                    "Only ready orders can be marked as served.",
                    "warning"
                )

                return redirect(
                    url_for("receptionist.orders")
                )

            db.execute("""
                UPDATE orders

                SET status = 'served'

                WHERE id = %s
            """, (order_id,))

            message = (
                f"Order #{order_id} has been served. "
                f"The table must now be cleared before another customer can use its QR code."
            )
            flash(message, "success")

            if self._wants_json():
                return jsonify({
                    "success": True,
                    "order_id": order_id,
                    "status": "served",
                    "message": message,
                })

            return redirect(
                url_for("receptionist.orders")
            )

        finally:
            db.close()

    # =========================================================
    # CLEAR TABLE (FINAL WORKFLOW)
    # =========================================================

    def clear_table(self, table_id):
        """Release a table only after every order is completed or cancelled."""
        db = Database()
        try:
            table = db.fetch_one(
                "SELECT id, name FROM restaurant_tables WHERE id = %s",
                (table_id,)
            )
            if not table:
                flash("Table not found.", "danger")
                return redirect(url_for("receptionist.dashboard"))

            active = db.fetch_one("""
                SELECT id FROM orders
                WHERE table_id = %s
                  AND status IN ('Placed', 'pending', 'preparing', 'ready')
                LIMIT 1
            """, (table_id,))
            if active:
                flash(
                    f"{table['name']} cannot be cleared while an order is active.",
                    "warning"
                )
                return redirect(url_for("receptionist.dashboard"))

            db.execute("""
                UPDATE orders
                SET status = 'cleared'
                WHERE table_id = %s
                  AND status IN ('served', 'cancelled')
            """, (table_id,))
            db.execute(
                "UPDATE restaurant_tables SET status = 'available' WHERE id = %s",
                (table_id,)
            )
            message = f"{table['name']} is now available for a new customer order."
            flash(message, "success")

            if self._wants_json():
                return jsonify({
                    "success": True,
                    "table_id": table_id,
                    "message": message,
                })

            return redirect(url_for("receptionist.dashboard"))
        finally:
            db.close()

    # =========================================================
    # CANCEL ORDER
    # =========================================================

    def cancel_order(self, order_id):
        """
        Cancel an order.

        The order is not deleted.

        It remains in the database so the manager can see
        the order history.
        """

        db = Database()

        try:

            order = db.fetch_one("""
                SELECT
                    id,
                    status
                FROM orders
                WHERE id = %s
            """, (order_id,))

            if not order:

                flash(
                    "Order not found.",
                    "danger"
                )

                return redirect(
                    url_for("receptionist.orders")
                )

            if order["status"] in (
                "served",
                "cleared",
                "cancelled"
            ):

                flash(
                    "This order can no longer be cancelled.",
                    "warning"
                )

                return redirect(
                    url_for("receptionist.orders")
                )

            db.execute("""
                UPDATE orders

                SET status = 'cancelled'

                WHERE id = %s
            """, (order_id,))

            message = f"Order #{order_id} has been cancelled."
            flash(message, "warning")

            if self._wants_json():
                return jsonify({
                    "success": True,
                    "order_id": order_id,
                    "status": "cancelled",
                    "message": message,
                })

            return redirect(
                url_for("receptionist.orders")
            )

        finally:
            db.close()

    # =========================================================
    # SAVE ORDER NOTE
    # =========================================================

    def save_order_note(self, order_id):
        note = request.form.get("receptionist_note", "").strip()

        if len(note) > 1000:
            flash("Order note cannot exceed 1000 characters.", "danger")
            return redirect(url_for("receptionist.orders"))

        db = Database()
        try:
            order = db.fetch_one(
                "SELECT id FROM orders WHERE id = %s",
                (order_id,),
            )
            if not order:
                flash("Order not found.", "danger")
                return redirect(url_for("receptionist.orders"))

            db.execute("""
                UPDATE orders
                SET receptionist_note = %s
                WHERE id = %s
            """, (note or None, order_id))
            flash(f"Note saved for order #{order_id}.", "success")
        except Exception:
            flash("Unable to save the order note.", "danger")
        finally:
            db.close()

        return redirect(url_for("receptionist.orders"))

    # =========================================================
    # SETTLE ORDER PAYMENT
    # =========================================================

    def settle_order(self, order_id):
        payment_method = request.form.get("payment_method", "cash").strip().lower()
        allowed_methods = {"cash", "card", "qr", "online", "other"}

        if payment_method not in allowed_methods:
            flash("Choose a valid payment method.", "danger")
            return redirect(url_for("receptionist.orders"))

        try:
            amount = round(float(request.form.get("amount", "")), 2)
        except (TypeError, ValueError):
            flash("Payment amount must be a valid number.", "danger")
            return redirect(url_for("receptionist.orders"))

        if amount < 0:
            flash("Payment amount cannot be negative.", "danger")
            return redirect(url_for("receptionist.orders"))

        db = Database()
        try:
            order = db.fetch_one("""
                SELECT id, status, total_amount
                FROM orders
                WHERE id = %s
            """, (order_id,))

            if not order:
                flash("Order not found.", "danger")
                return redirect(url_for("receptionist.orders"))

            if order["status"] in ("cancelled", "cleared"):
                flash("Cancelled or cleared orders cannot receive a new payment.", "warning")
                return redirect(url_for("receptionist.orders"))

            total = round(float(order["total_amount"] or 0), 2)
            if abs(amount - total) > 0.01:
                flash(
                    f"Payment must match the order total of Rs. {total:.2f}.",
                    "danger",
                )
                return redirect(url_for("receptionist.orders"))

            existing_payment = db.fetch_one("""
                SELECT id
                FROM payments
                WHERE order_id = %s
                  AND payment_status = 'paid'
                ORDER BY id DESC
                LIMIT 1
            """, (order_id,))

            if existing_payment:
                flash("This order has already been paid.", "warning")
                return redirect(url_for("receptionist.orders"))

            pending_payment = db.fetch_one("""
                SELECT id
                FROM payments
                WHERE order_id = %s
                  AND payment_status <> 'paid'
                ORDER BY id DESC
                LIMIT 1
            """, (order_id,))

            if pending_payment:
                db.execute("""
                    UPDATE payments
                    SET amount = %s,
                        payment_method = %s,
                        payment_status = 'paid',
                        paid_at = NOW()
                    WHERE id = %s
                """, (amount, payment_method, pending_payment["id"]))
            else:
                db.execute("""
                    INSERT INTO payments
                        (order_id, amount, payment_method, payment_status, paid_at)
                    VALUES (%s, %s, %s, 'paid', NOW())
                """, (order_id, amount, payment_method))

            message = f"Payment recorded for order #{order_id}."
            flash(message, "success")
            if self._wants_json():
                return jsonify({
                    "success": True,
                    "order_id": order_id,
                    "message": message,
                })
        except Exception:
            flash("Unable to record payment. Please try again.", "danger")
        finally:
            db.close()

        return redirect(url_for("receptionist.orders"))

    # =========================================================
    # LIVE ORDER FEED
    # =========================================================

    def live_orders(self):
        """Return the active order queue for no-reload receptionist updates."""
        db = Database()
        try:
            orders = db.fetch_all("""
                SELECT
                    o.id,
                    COALESCE(o.order_number, o.id) AS order_number,
                    o.table_id,
                    t.name AS table_name,
                    o.status,
                    COALESCE(o.total_amount, 0) AS total,
                    o.receptionist_note,
                    o.created_at,
                    COALESCE(p.payment_status, 'unpaid') AS payment_status,
                    COALESCE(p.payment_method, '') AS payment_method
                FROM orders o
                LEFT JOIN restaurant_tables t
                    ON o.table_id = t.id
                LEFT JOIN payments p
                    ON p.id = (
                        SELECT MAX(p2.id)
                        FROM payments p2
                        WHERE p2.order_id = o.id
                    )
                WHERE o.status IN ('Placed', 'pending', 'preparing', 'ready', 'served')
                ORDER BY o.created_at DESC, o.id DESC
            """)

            for order in orders:
                order["created_at"] = str(order.get("created_at") or "")
                order["total"] = float(order.get("total") or 0)
                order["items"] = db.fetch_all("""
                    SELECT
                        mi.name,
                        oi.quantity,
                        (oi.quantity * oi.price_at_order) AS subtotal
                    FROM order_items oi
                    LEFT JOIN menu_items mi ON mi.id = oi.item_id
                    WHERE oi.order_id = %s
                    ORDER BY oi.id ASC
                """, (order["id"],))
                for item in order["items"]:
                    item["quantity"] = int(item.get("quantity") or 0)
                    item["subtotal"] = float(item.get("subtotal") or 0)

            tables = db.fetch_all("""
                SELECT
                    t.id,
                    t.name,
                    t.status,
                    (
                        SELECT o.id
                        FROM orders o
                        WHERE o.table_id = t.id
                          AND o.status IN ('Placed', 'pending', 'preparing', 'ready', 'served')
                        ORDER BY o.id DESC
                        LIMIT 1
                    ) AS current_order_id
                FROM restaurant_tables t
                ORDER BY t.id ASC
            """)

            return jsonify({
                "orders": orders,
                "count": len(orders),
                "tables": tables,
            })
        finally:
            db.close()

    # =========================================================
    # NOTIFICATIONS
    # =========================================================

    def notifications(self):
        """
        Return pending orders for receptionist notifications.
        """

        db = Database()

        try:

            notifications = db.fetch_all("""
                SELECT
                    o.id,
                    o.id AS order_number,
                    o.table_id,
                    t.name AS table_name,
                    o.status,
                    o.created_at

                FROM orders o

                LEFT JOIN restaurant_tables t
                    ON o.table_id = t.id

                WHERE o.status IN ('Placed', 'pending')

                ORDER BY o.id DESC
            """)

            return {
                "count": len(notifications),
                "orders": notifications
            }

        finally:
            db.close()

    # =========================================================
    # VIEW SINGLE ORDER
    # =========================================================

    def view_order(self, order_id):
        """
        Display complete information about a specific order.
        """

        db = Database()

        try:

            # -------------------------------------------------
            # Get order
            # -------------------------------------------------

            order = db.fetch_one("""
                SELECT
                    orders.id,
                    orders.table_id,
                    orders.created_at,
                    orders.status,

                    restaurant_tables.name AS table_name

                FROM orders

                LEFT JOIN restaurant_tables
                    ON orders.table_id = restaurant_tables.id

                WHERE orders.id = %s
            """, (order_id,))

            if not order:

                flash(
                    "Order not found.",
                    "danger"
                )

                return redirect(
                    url_for("receptionist.dashboard")
                )

            # -------------------------------------------------
            # Get order items
            # -------------------------------------------------

            order["items"] = db.fetch_all("""
                SELECT
                    order_items.quantity,
                    order_items.price_at_order,

                    menu_items.name

                FROM order_items

                INNER JOIN menu_items
                    ON order_items.item_id = menu_items.id

                WHERE order_items.order_id = %s

                ORDER BY order_items.id ASC
            """, (order_id,))

            # -------------------------------------------------
            # Calculate total
            # -------------------------------------------------

            order["total"] = 0

            for item in order["items"]:

                order["total"] += (
                    float(item["price_at_order"])
                    * int(item["quantity"])
                )

            return render_template(
                "receptionist/view_order.html",
                order=order
            )

        finally:
            db.close()