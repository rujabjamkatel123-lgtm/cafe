"""
=============================================================
  Restaurant Management System - Manager Controller
=============================================================
"""

import os
import uuid
from io import BytesIO

import qrcode

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
    send_file
)

from werkzeug.utils import secure_filename

import config

from app.controllers.base_controllers import BaseController
from app.modules.database import Database


class ManagerController(BaseController):
    """
    Controller for all manager operations.
    """

    # =========================================================
    # DATABASE COMPATIBILITY
    # =========================================================

    def _ensure_half_plate_column(self):
        """
        Make sure menu_items has half_plate_price column.
        """

        db = Database()

        try:
            column = db.fetch_one("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'menu_items'
                  AND COLUMN_NAME = 'half_plate_price'
            """)

            if not column:
                db.execute("""
                    ALTER TABLE menu_items
                    ADD COLUMN half_plate_price DECIMAL(10,2) NULL
                    AFTER price
                """)

        except Exception as e:
            print(
                "Half plate column check:",
                e
            )

        finally:
            db.close()

    # =========================================================
    # MANAGER DASHBOARD
    # =========================================================

    def dashboard(self):

        db = Database()

        try:

            today_sales = db.fetch_one("""
                SELECT
                    COALESCE(
                        SUM(
                            oi.quantity *
                            oi.price_at_order
                        ),
                        0
                    ) AS total_sales
                FROM orders o

                JOIN order_items oi
                    ON o.id = oi.order_id

                WHERE DATE(o.created_at) = CURDATE()
                  AND o.status = 'cleared'
            """)

            today_orders = db.fetch_one("""
                SELECT
                    COUNT(*) AS total
                FROM orders

                WHERE DATE(created_at) = CURDATE()
                  AND status = 'cleared'
            """)

            today_items = db.fetch_one("""
                SELECT
                    COALESCE(
                        SUM(oi.quantity),
                        0
                    ) AS total_items
                FROM orders o

                JOIN order_items oi
                    ON o.id = oi.order_id

                WHERE DATE(o.created_at) = CURDATE()
                  AND o.status = 'cleared'
            """)

            daily_sales = db.fetch_all("""
                SELECT DATE(o.created_at) AS sale_date,
                       COALESCE(SUM(o.total_amount), 0) AS total_sales
                FROM orders o
                WHERE o.created_at >= CURDATE() - INTERVAL 6 DAY
                  AND o.status = 'cleared'
                GROUP BY DATE(o.created_at)
                ORDER BY sale_date ASC
            """)

            recent_orders = db.fetch_all("""
                SELECT
                    o.id,
                    o.order_number,
                    t.name AS table_name,
                    o.status,
                    o.created_at,

                    COALESCE(
                        SUM(
                            oi.quantity *
                            oi.price_at_order
                        ),
                        0
                    ) AS total

                FROM orders o

                LEFT JOIN restaurant_tables t
                    ON o.table_id = t.id

                LEFT JOIN order_items oi
                    ON o.id = oi.order_id

                GROUP BY
                    o.id,
                    o.order_number,
                    t.name,
                    o.status,
                    o.created_at

                ORDER BY o.id DESC

                LIMIT 10
            """)

        finally:
            db.close()

        return render_template(
            "manager/dashboard.html",
            today_sales=(
                today_sales["total_sales"]
                if today_sales
                else 0
            ),
            today_orders=(
                today_orders["total"]
                if today_orders
                else 0
            ),
            today_items=(
                today_items["total_items"]
                if today_items
                else 0
            ),
            recent_orders=recent_orders,
            sales_chart=self._build_sales_chart(daily_sales),
            table_qr_codes=[
                {
                    "number": table_number,
                    "url": self._customer_table_url(table_number),
                    "image_url": url_for("manager.table_qr", table_id=table_number),
                    "download_url": url_for("manager.download_table_qr", table_id=table_number),
                }
                for table_number in range(1, 6)
            ]
        )

    def table_qr_page(self):
        """Render the manager view for printing and downloading table QR codes."""
        table_qr_codes = [
            {
                "number": table_number,
                "url": self._customer_table_url(table_number),
                "image_url": url_for(
                    "manager.table_qr",
                    table_id=table_number,
                ),
                "download_url": url_for(
                    "manager.download_table_qr",
                    table_id=table_number,
                ),
            }
            for table_number in range(1, 6)
        ]

        return render_template(
            "manager/table_qr.html",
            table_qr_codes=table_qr_codes,
        )

    def _build_sales_chart(self, daily_sales):
        """Return seven real calendar-day values for the dashboard chart."""
        from datetime import date, timedelta
        values = {
            row["sale_date"].isoformat(): float(row["total_sales"] or 0)
            for row in daily_sales
        }
        days = [date.today() - timedelta(days=offset) for offset in range(6, -1, -1)]
        amounts = [values.get(day.isoformat(), 0.0) for day in days]
        maximum = max(amounts, default=0.0)
        return [
            {
                "label": day.strftime("%a"),
                "date": day.isoformat(),
                "amount": amount,
                "height": round((amount / maximum) * 100, 2) if maximum else 0,
            }
            for day, amount in zip(days, amounts)
        ]

    # =========================================================
    # TABLE QR CODES
    # =========================================================

    def _customer_table_url(self, table_id):
        customer_path = url_for("customer.entry", table=table_id)
        public_base_url = getattr(config, "PUBLIC_BASE_URL", "").rstrip("/")
        if public_base_url:
            return f"{public_base_url}{customer_path}"
        return url_for("customer.entry", _external=True, table=table_id)

    def _table_qr_payload(self, table_id):
        if table_id < 1 or table_id > 5:
            raise ValueError("Table must be between 1 and 5")
        return self._customer_table_url(table_id)

    def _qr_response(self, table_id, download=False):
        payload = self._table_qr_payload(table_id)
        image = qrcode.make(payload)
        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return send_file(
            output,
            mimetype="image/png",
            as_attachment=download,
            download_name=f"table-{table_id}-qr.png",
        )

    def table_qr(self, table_id):
        return self._qr_response(table_id)

    def download_table_qr(self, table_id):
        return self._qr_response(table_id, download=True)

    # =========================================================
    # REPORTS
    # =========================================================

    def reports(self):

        start_date = request.args.get(
            "start_date"
        )

        end_date = request.args.get(
            "end_date"
        )

        db = Database()

        try:

            if start_date and end_date:

                sales = db.fetch_one("""
                    SELECT
                        COALESCE(
                            SUM(
                                oi.quantity *
                                oi.price_at_order
                            ),
                            0
                        ) AS total_sales

                    FROM orders o

                    JOIN order_items oi
                        ON o.id = oi.order_id

                    WHERE DATE(o.created_at)
                          BETWEEN %s AND %s

                      AND o.status = 'cleared'
                """, (
                    start_date,
                    end_date
                ))

                order_count = db.fetch_one("""
                    SELECT
                        COUNT(*) AS total

                    FROM orders

                    WHERE DATE(created_at)
                          BETWEEN %s AND %s

                      AND status = 'cleared'
                """, (
                    start_date,
                    end_date
                ))

                item_count = db.fetch_one("""
                    SELECT
                        COALESCE(
                            SUM(oi.quantity),
                            0
                        ) AS total_items

                    FROM orders o

                    JOIN order_items oi
                        ON o.id = oi.order_id

                    WHERE DATE(o.created_at)
                          BETWEEN %s AND %s

                      AND o.status = 'cleared'
                """, (
                    start_date,
                    end_date
                ))

                popular_items = db.fetch_all("""
                    SELECT
                        m.name,

                        SUM(
                            oi.quantity
                        ) AS quantity_sold,

                        SUM(
                            oi.quantity *
                            oi.price_at_order
                        ) AS revenue

                    FROM order_items oi

                    JOIN orders o
                        ON oi.order_id = o.id

                    JOIN menu_items m
                        ON oi.item_id = m.id

                    WHERE DATE(o.created_at)
                          BETWEEN %s AND %s

                      AND o.status = 'cleared'

                    GROUP BY
                        m.id,
                        m.name

                    ORDER BY
                        quantity_sold DESC
                """, (
                    start_date,
                    end_date
                ))

            else:

                sales = db.fetch_one("""
                    SELECT
                        COALESCE(
                            SUM(
                                oi.quantity *
                                oi.price_at_order
                            ),
                            0
                        ) AS total_sales

                    FROM orders o

                    JOIN order_items oi
                        ON o.id = oi.order_id

                    WHERE DATE(o.created_at) = CURDATE()
                      AND o.status = 'cleared'
                """)

                order_count = db.fetch_one("""
                    SELECT
                        COUNT(*) AS total

                    FROM orders

                    WHERE DATE(created_at) = CURDATE()
                      AND status = 'cleared'
                """)

                item_count = db.fetch_one("""
                    SELECT
                        COALESCE(
                            SUM(oi.quantity),
                            0
                        ) AS total_items

                    FROM orders o

                    JOIN order_items oi
                        ON o.id = oi.order_id

                    WHERE DATE(o.created_at) = CURDATE()
                      AND o.status = 'cleared'
                """)

                popular_items = db.fetch_all("""
                    SELECT
                        m.name,

                        SUM(
                            oi.quantity
                        ) AS quantity_sold,

                        SUM(
                            oi.quantity *
                            oi.price_at_order
                        ) AS revenue

                    FROM order_items oi

                    JOIN orders o
                        ON oi.order_id = o.id

                    JOIN menu_items m
                        ON oi.item_id = m.id

                    WHERE DATE(o.created_at) = CURDATE()
                      AND o.status = 'cleared'

                    GROUP BY
                        m.id,
                        m.name

                    ORDER BY
                        quantity_sold DESC
                """)

        finally:
            db.close()

        return render_template(
            "manager/reports.html",
            total_sales=(
                sales["total_sales"]
                if sales
                else 0
            ),
            total_orders=(
                order_count["total"]
                if order_count
                else 0
            ),
            total_items=(
                item_count["total_items"]
                if item_count
                else 0
            ),
            popular_items=popular_items,
            start_date=start_date,
            end_date=end_date
        )

    # =========================================================
    # REPORTS (FINAL DATABASE-DRIVEN FLOW)
    # =========================================================

    def reports(self):
        from datetime import date
        start_date = request.args.get("start_date") or date.today().isoformat()
        end_date = request.args.get("end_date") or start_date
        params = (start_date, end_date)
        db = Database()
        try:
            summary = db.fetch_one("""
                SELECT COUNT(*) AS total_orders,
                       COALESCE(SUM(o.total_amount), 0) AS total_sales,
                       COALESCE((
                           SELECT SUM(oi.quantity)
                           FROM order_items oi
                           JOIN orders item_orders ON item_orders.id = oi.order_id
                           WHERE DATE(item_orders.created_at) BETWEEN %s AND %s
                             AND item_orders.status = 'cleared'
                       ), 0) AS total_items
                FROM orders o
                WHERE DATE(o.created_at) BETWEEN %s AND %s
                  AND o.status = 'cleared'
            """, (start_date, end_date, start_date, end_date))
            sales_data = db.fetch_all("""
                SELECT DATE(o.created_at) AS period,
                       COALESCE(SUM(o.total_amount), 0) AS sales
                FROM orders o
                WHERE DATE(o.created_at) BETWEEN %s AND %s
                  AND o.status = 'cleared'
                GROUP BY DATE(o.created_at)
                ORDER BY period ASC
            """, params)
            category_sales = db.fetch_all("""
                SELECT COALESCE(mc.name, 'Uncategorized') AS category,
                       COALESCE(SUM(oi.quantity), 0) AS quantity,
                       COALESCE(SUM(oi.quantity * oi.price_at_order), 0) AS sales
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                LEFT JOIN menu_items mi ON mi.id = oi.item_id
                LEFT JOIN menu_categories mc ON mc.id = mi.category_id
                WHERE DATE(o.created_at) BETWEEN %s AND %s
                  AND o.status = 'cleared'
                GROUP BY mc.id, mc.name
                ORDER BY sales DESC
            """, params)
            best_selling_items = db.fetch_all("""
                SELECT mi.name, COALESCE(mc.name, 'Uncategorized') AS category,
                       SUM(oi.quantity) AS quantity,
                       SUM(oi.quantity * oi.price_at_order) AS sales
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                JOIN menu_items mi ON mi.id = oi.item_id
                LEFT JOIN menu_categories mc ON mc.id = mi.category_id
                WHERE DATE(o.created_at) BETWEEN %s AND %s
                  AND o.status = 'cleared'
                GROUP BY mi.id, mi.name, mc.name
                ORDER BY quantity DESC, sales DESC
                LIMIT 10
            """, params)
        finally:
            db.close()
        summary = summary or {}
        return render_template(
            "manager/reports.html",
            total_sales=float(summary.get("total_sales", 0) or 0),
            total_orders=int(summary.get("total_orders", 0) or 0),
            total_items=int(summary.get("total_items", 0) or 0),
            total_items_sold=int(summary.get("total_items", 0) or 0),
            total_profit=float(summary.get("total_sales", 0) or 0),
            sales_data=sales_data,
            category_sales=category_sales,
            best_selling_items=best_selling_items,
            popular_items=best_selling_items,
            start_date=start_date,
            end_date=end_date
        )

    # =========================================================
    # ORDER HISTORY
    # =========================================================

    def history(self):

        start_date = request.args.get(
            "start_date"
        )

        end_date = request.args.get(
            "end_date"
        )

        db = Database()

        query = """
            SELECT
                o.id,
                o.order_number,
                t.name AS table_name,
                o.status,
                o.created_at,

                COALESCE(o.total_amount, 0) AS total

            FROM orders o

            LEFT JOIN restaurant_tables t
                ON o.table_id = t.id

            LEFT JOIN order_items oi
                ON o.id = oi.order_id
        """

        params = []

        if start_date and end_date:

            query += """
                WHERE DATE(o.created_at)
                BETWEEN %s AND %s
            """

            params.extend([
                start_date,
                end_date
            ])

        query += """
            GROUP BY
                o.id,
                o.order_number,
                t.name,
                o.status,
                o.created_at

            ORDER BY
                o.created_at DESC
        """

        try:

            orders = db.fetch_all(
                query,
                tuple(params) if params else None
            )
            for order in orders:
                order["items"] = db.fetch_all("""
                    SELECT oi.item_id, mi.name, oi.quantity, oi.price_at_order,
                           (oi.quantity * oi.price_at_order) AS subtotal
                    FROM order_items oi
                    LEFT JOIN menu_items mi ON mi.id = oi.item_id
                    WHERE oi.order_id = %s
                    ORDER BY oi.id ASC
                """, (order["id"],))

        finally:
            db.close()

        total_revenue = sum(float(order.get("total") or 0) for order in orders)
        total_items_sold = sum(
            int(item.get("quantity") or 0)
            for order in orders
            for item in order.get("items", [])
        )
        return render_template(
            "manager/history.html",
            orders=orders,
            total_orders=len(orders),
            total_revenue=total_revenue,
            total_items_sold=total_items_sold,
            start_date=start_date,
            end_date=end_date
        )

    # =========================================================
    # ORDER DETAILS
    # =========================================================

    def order_details(self, order_id):

        db = Database()

        try:

            order = db.fetch_one("""
                SELECT
                    o.id,
                    o.table_id,
                    t.name AS table_name,
                    o.status,
                    o.created_at

                FROM orders o

                LEFT JOIN restaurant_tables t
                    ON o.table_id = t.id

                WHERE o.id = %s
            """, (
                order_id,
            ))

            if not order:

                flash(
                    "Order not found.",
                    "danger"
                )

                return redirect(
                    url_for("manager.history")
                )

            items = db.fetch_all("""
                SELECT
                    oi.id,
                    m.name AS item_name,
                    oi.quantity,
                    oi.price_at_order,

                    (
                        oi.quantity *
                        oi.price_at_order
                    ) AS subtotal

                FROM order_items oi

                JOIN menu_items m
                    ON oi.item_id = m.id

                WHERE oi.order_id = %s

                ORDER BY oi.id ASC
            """, (
                order_id,
            ))

        finally:
            db.close()

        total = sum(
            float(item["subtotal"])
            for item in items
        )

        return render_template(
            "manager/order_details.html",
            order=order,
            items=items,
            total=total
        )

    # =========================================================
    # DAILY SALES
    # =========================================================

    def daily_sales(self):

        db = Database()

        try:

            daily_sales = db.fetch_all("""
                SELECT
                    DATE(o.created_at)
                    AS sale_date,

                    COALESCE(
                        SUM(
                            oi.quantity *
                            oi.price_at_order
                        ),
                        0
                    ) AS total_sales

                FROM orders o

                JOIN order_items oi
                    ON o.id = oi.order_id

                WHERE o.status != 'cancelled'

                GROUP BY
                    DATE(o.created_at)

                ORDER BY
                    sale_date DESC

                LIMIT 30
            """)

        finally:
            db.close()

        return daily_sales

    # =========================================================
    # MONTHLY SALES
    # =========================================================

    def monthly_sales(self):

        db = Database()

        try:

            monthly_sales = db.fetch_all("""
                SELECT
                    YEAR(o.created_at)
                    AS sale_year,

                    MONTH(o.created_at)
                    AS sale_month,

                    COALESCE(
                        SUM(
                            oi.quantity *
                            oi.price_at_order
                        ),
                        0
                    ) AS total_sales

                FROM orders o

                JOIN order_items oi
                    ON o.id = oi.order_id

                WHERE o.status != 'cancelled'

                GROUP BY
                    YEAR(o.created_at),
                    MONTH(o.created_at)

                ORDER BY
                    sale_year DESC,
                    sale_month DESC
            """)

        finally:
            db.close()

        return monthly_sales

    # =========================================================
    # MENU PERFORMANCE
    # =========================================================

    def menu_performance(self):

        db = Database()

        try:

            items = db.fetch_all("""
                SELECT
                    m.id,
                    m.name,
                    m.price,

                    COALESCE(
                        SUM(oi.quantity),
                        0
                    ) AS quantity_sold,

                    COALESCE(
                        SUM(
                            oi.quantity *
                            oi.price_at_order
                        ),
                        0
                    ) AS revenue

                FROM menu_items m

                LEFT JOIN order_items oi
                    ON m.id = oi.item_id

                LEFT JOIN orders o
                    ON oi.order_id = o.id
                   AND o.status = 'cleared'

                GROUP BY
                    m.id,
                    m.name,
                    m.price

                ORDER BY
                    quantity_sold DESC
            """)

        finally:
            db.close()

        return items

    # =========================================================
    # MENU MANAGEMENT
    # =========================================================

    def menu(self):

        self._ensure_half_plate_column()

        db = Database()

        try:

            menu_items = db.fetch_all("""
                SELECT
                    menu_items.id,
                    menu_items.name,
                    menu_items.price,
                    menu_items.half_plate_price,
                    menu_items.category_id,
                    menu_items.description,
                    menu_items.image,
                    menu_items.available,

                    menu_categories.name AS category

                FROM menu_items

                LEFT JOIN menu_categories
                    ON menu_items.category_id =
                    menu_categories.id

                ORDER BY
                    FIELD(menu_categories.name, 'Starter', 'Main Course', 'Drinks', 'Dessert'),
                    menu_items.name
            """)

            categories = db.fetch_all("""
                SELECT *
                FROM menu_categories
                ORDER BY FIELD(name, 'Starter', 'Main Course', 'Drinks', 'Dessert'), name
            """)

        finally:

            db.close()

        return render_template(
            "manager/menu.html",
            menu_items=menu_items,
            categories=categories
        )

    # =========================================================
    # MENU IMAGE UPLOAD
    # =========================================================

    def _save_menu_image(self):
        uploaded = request.files.get("image")
        if not uploaded or not uploaded.filename:
            return None

        filename = secure_filename(uploaded.filename)
        extension = os.path.splitext(filename)[1].lower()
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        if extension not in allowed_extensions:
            raise ValueError("Please upload a JPG, JPEG, PNG, WEBP, or GIF image.")

        stored_name = f"menu-{uuid.uuid4().hex}{extension}"
        upload_dir = os.path.join(current_app.static_folder, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        uploaded.save(os.path.join(upload_dir, stored_name))
        return stored_name

    # =========================================================
    # ADD MENU ITEM
    # =========================================================

    def add_menu_item(self):

        self._ensure_half_plate_column()

        # -----------------------------------------------------
        # GET
        # -----------------------------------------------------

        if request.method == "GET":

            return redirect(
                url_for("manager.menu")
            )

        # -----------------------------------------------------
        # POST
        # -----------------------------------------------------

        name = request.form.get(
            "name",
            ""
        ).strip()

        # Accept category_id from the new form
        category_id = request.form.get(
            "category_id",
            ""
        ).strip()

        # Also accept category from your existing form
        category = request.form.get(
            "category",
            ""
        ).strip()

        full_price = request.form.get(
            "price",
            ""
        ).strip()

        half_price = request.form.get(
            "half_plate_price",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        available = (
            1
            if request.form.get("available")
            else 0
        )

        # =====================================================
        # VALIDATION
        # =====================================================

        if not name:

            flash(
                "Food name is required.",
                "danger"
            )

            return redirect(
                url_for("manager.menu")
            )

        if not category_id and not category:

            flash(
                "Category is required.",
                "danger"
            )

            return redirect(
                url_for("manager.menu")
            )

        if not full_price:

            flash(
                "Full plate price is required.",
                "danger"
            )

            return redirect(
                url_for("manager.menu")
            )

        # =====================================================
        # CONVERT CATEGORY NAME TO CATEGORY ID
        # =====================================================

        if not category_id and category:

            category_mapping = {
                "Main-Course": 1,
                "Main Course": 1,
                "Appetizers": 2,
                "Beverages": 3,
                "Desserts": 4
            }

            category_id = category_mapping.get(
                category
            )

        if not category_id:

            flash(
                "Invalid category selected.",
                "danger"
            )

            return redirect(
                url_for("manager.menu")
            )

        # =====================================================
        # CONVERT CATEGORY ID
        # =====================================================

        try:

            category_id = int(
                category_id
            )

        except (
            ValueError,
            TypeError
        ):

            flash(
                "Invalid category.",
                "danger"
            )

            return redirect(
                url_for("manager.menu")
            )

        # =====================================================
        # CONVERT PRICES
        # =====================================================

        try:

            full_price_value = float(
                full_price
            )

            if full_price_value < 0:
                raise ValueError

            if half_price:

                half_price_value = float(
                    half_price
                )

                if half_price_value < 0:
                    raise ValueError

            else:

                half_price_value = None

        except (
            ValueError,
            TypeError
        ):

            flash(
                "Please enter valid prices.",
                "danger"
            )

            return redirect(
                url_for("manager.menu")
            )

        # =====================================================
        # SAVE OPTIONAL IMAGE
        # =====================================================

        try:
            image_name = self._save_menu_image()
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("manager.menu"))

        # =====================================================
        # DATABASE INSERT
        # =====================================================

        db = Database()

        try:

            db.execute("""
                INSERT INTO menu_items
                (
                    name,
                    price,
                    half_plate_price,
                    category_id,
                    description,
                    image,
                    available
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                name,
                full_price_value,
                half_price_value,
                category_id,
                description,
                image_name,
                available
            ))

            flash(
                "Menu item added successfully!",
                "success"
            )

        except Exception as e:

            print(
                "ADD MENU ITEM ERROR:",
                e
            )

            flash(
                f"Error adding menu item: {e}",
                "danger"
            )

        finally:

            db.close()

        return redirect(
            url_for("manager.menu")
        )

    # =========================================================
    # EDIT MENU ITEM
    # =========================================================

    def edit_menu_item(self, item_id):

        self._ensure_half_plate_column()

        db = Database()

        try:

            item = db.fetch_one("""
                SELECT *
                FROM menu_items
                WHERE id = %s
            """, (
                item_id,
            ))

            if not item:

                flash(
                    "Menu item not found.",
                    "danger"
                )

                return redirect(
                    url_for("manager.menu")
                )

            if request.method == "POST":

                name = request.form.get(
                    "name",
                    ""
                ).strip()

                category_id = request.form.get(
                    "category_id",
                    ""
                ).strip()

                category = request.form.get(
                    "category",
                    ""
                ).strip()

                full_price = request.form.get(
                    "price",
                    ""
                ).strip()

                half_price = request.form.get(
                    "half_plate_price",
                    ""
                ).strip()

                description = request.form.get(
                    "description",
                    ""
                ).strip()

                available = (
                    1
                    if request.form.get("available")
                    else 0
                )

                if not category_id and category:

                    category_mapping = {
                        "Main-Course": 1,
                        "Main Course": 1,
                        "Appetizers": 2,
                        "Beverages": 3,
                        "Desserts": 4
                    }

                    category_id = category_mapping.get(
                        category
                    )

                if not name or not category_id or not full_price:

                    flash(
                        "Name, category and price are required.",
                        "danger"
                    )

                    return redirect(
                        request.referrer or
                        url_for("manager.menu")
                    )

                try:

                    image_name = self._save_menu_image()

                    category_id = int(
                        category_id
                    )

                    full_price_value = float(
                        full_price
                    )

                    if half_price:

                        half_price_value = float(
                            half_price
                        )

                    else:

                        half_price_value = None

                except (
                    ValueError,
                    TypeError
                ):

                    flash(
                        "Please enter valid values.",
                        "danger"
                    )

                    return redirect(
                        request.referrer or
                        url_for("manager.menu")
                    )

                update_sql = """
                    UPDATE menu_items
                    SET
                        name = %s,
                        price = %s,
                        half_plate_price = %s,
                        category_id = %s,
                        description = %s,
                        available = %s
                """
                update_values = [
                    name,
                    full_price_value,
                    half_price_value,
                    category_id,
                    description,
                    available,
                ]

                if image_name:
                    update_sql += ", image = %s"
                    update_values.append(image_name)

                update_sql += " WHERE id = %s"
                update_values.append(item_id)
                db.execute(update_sql, tuple(update_values))

                flash(
                    "Menu item updated successfully!",
                    "success"
                )

                return redirect(
                    url_for("manager.menu")
                )

            categories = db.fetch_all("""
                SELECT *
                FROM menu_categories
                ORDER BY FIELD(name, 'Starter', 'Main Course', 'Drinks', 'Dessert'), name
            """)

        finally:
            db.close()

        return render_template(
            "manager/edit_menu_item.html",
            item=item,
            categories=categories
        )

    # =========================================================
    # DELETE MENU ITEM
    # =========================================================

    def delete_menu_item(self, item_id):

        db = Database()

        try:

            item = db.fetch_one("""
                SELECT *
                FROM menu_items
                WHERE id = %s
            """, (
                item_id,
            ))

            if not item:

                flash(
                    "Menu item not found.",
                    "danger"
                )

                return redirect(
                    url_for("manager.menu")
                )

            # Preserve historical order_items references. The menu item is
            # archived from customer ordering instead of physically deleted.
            db.execute("""
                UPDATE menu_items
                SET available = 0
                WHERE id = %s
            """, (item_id,))

            flash(
                "Menu item archived successfully. Historical orders are preserved.",
                "success"
            )

        except Exception as e:

            print(
                "DELETE MENU ITEM ERROR:",
                e
            )

            flash(
                f"Unable to archive menu item: {e}",
                "danger"
            )

        finally:
            db.close()

        return redirect(
            url_for("manager.menu")
        )

    # =========================================================
    # PERMANENTLY DELETE MENU ITEM
    # =========================================================

    def permanently_delete_menu_item(self, item_id):
        """Delete an unused menu item permanently by its primary-key ID."""
        db = Database()

        try:
            item = db.fetch_one(
                """
                SELECT id, name
                FROM menu_items
                WHERE id = %s
                """,
                (item_id,),
            )

            if not item:
                flash("Menu item not found.", "danger")
                return redirect(url_for("manager.menu"))

            reference = db.fetch_one(
                """
                SELECT COUNT(*) AS total
                FROM order_items
                WHERE item_id = %s
                """,
                (item_id,),
            )

            if reference and int(reference.get("total") or 0) > 0:
                flash(
                    f"{item['name']} is used in order history and cannot be deleted permanently. Archive it instead.",
                    "danger",
                )
                return redirect(url_for("manager.menu"))

            # The primary-key predicate also works when MySQL safe updates are enabled.
            db.execute(
                "DELETE FROM menu_items WHERE id = %s",
                (item_id,),
            )
            flash(f"{item['name']} was deleted permanently.", "success")

        except Exception as error:
            print("PERMANENT MENU DELETE ERROR:", error)
            flash("Unable to delete the menu item permanently.", "danger")
        finally:
            db.close()

        return redirect(url_for("manager.menu"))

    # =========================================================
    # INVENTORY MANAGEMENT
    # =========================================================

    @staticmethod
    def _parse_inventory_number(value, field_name):
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_name} must be a valid number.")

        if number < 0:
            raise ValueError(f"{field_name} cannot be negative.")

        return round(number, 2)

    def inventory(self):
        db = Database()

        try:
            inventory_items = db.fetch_all("""
                SELECT
                    id,
                    name,
                    unit,
                    current_stock,
                    reorder_level,
                    cost_per_unit,
                    supplier,
                    notes,
                    active,
                    updated_at
                FROM inventory_items
                WHERE active = 1
                ORDER BY
                    CASE
                        WHEN current_stock <= reorder_level THEN 0
                        ELSE 1
                    END,
                    name ASC
            """)
        finally:
            db.close()

        low_stock_count = sum(
            1
            for item in inventory_items
            if float(item["current_stock"] or 0)
            <= float(item["reorder_level"] or 0)
        )
        out_of_stock_count = sum(
            1
            for item in inventory_items
            if float(item["current_stock"] or 0) <= 0
        )
        stock_value = sum(
            float(item["current_stock"] or 0)
            * float(item["cost_per_unit"] or 0)
            for item in inventory_items
        )

        return render_template(
            "manager/inventory.html",
            inventory_items=inventory_items,
            inventory_stats={
                "total_items": len(inventory_items),
                "low_stock": low_stock_count,
                "out_of_stock": out_of_stock_count,
                "stock_value": round(stock_value, 2),
            },
        )

    def add_inventory_item(self):
        name = request.form.get("name", "").strip()
        unit = request.form.get("unit", "unit").strip() or "unit"
        supplier = request.form.get("supplier", "").strip()
        notes = request.form.get("notes", "").strip()

        if not name:
            flash("Inventory item name is required.", "danger")
            return redirect(url_for("manager.inventory"))

        try:
            current_stock = self._parse_inventory_number(
                request.form.get("current_stock", "0"),
                "Current stock",
            )
            reorder_level = self._parse_inventory_number(
                request.form.get("reorder_level", "0"),
                "Reorder level",
            )
            cost_per_unit = self._parse_inventory_number(
                request.form.get("cost_per_unit", "0"),
                "Cost per unit",
            )
        except ValueError as error:
            flash(str(error), "danger")
            return redirect(url_for("manager.inventory"))

        db = Database()
        try:
            db.execute("""
                INSERT INTO inventory_items
                    (name, unit, current_stock, reorder_level,
                     cost_per_unit, supplier, notes, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
            """, (
                name,
                unit,
                current_stock,
                reorder_level,
                cost_per_unit,
                supplier or None,
                notes or None,
            ))

            new_item = db.fetch_one("""
                SELECT id
                FROM inventory_items
                WHERE name = %s
                ORDER BY id DESC
                LIMIT 1
            """, (name,))

            if new_item and current_stock > 0:
                db.execute("""
                    INSERT INTO inventory_movements
                        (inventory_item_id, change_amount, stock_after, reason)
                    VALUES (%s, %s, %s, %s)
                """, (
                    new_item["id"],
                    current_stock,
                    current_stock,
                    "Opening stock",
                ))

            flash("Inventory item added successfully.", "success")
        except Exception:
            flash("Unable to add inventory item. Check the values and try again.", "danger")
        finally:
            db.close()

        return redirect(url_for("manager.inventory"))

    def update_inventory_item(self, item_id):
        name = request.form.get("name", "").strip()
        unit = request.form.get("unit", "unit").strip() or "unit"
        supplier = request.form.get("supplier", "").strip()
        notes = request.form.get("notes", "").strip()

        if not name:
            flash("Inventory item name is required.", "danger")
            return redirect(url_for("manager.inventory"))

        try:
            current_stock = self._parse_inventory_number(
                request.form.get("current_stock", "0"),
                "Current stock",
            )
            reorder_level = self._parse_inventory_number(
                request.form.get("reorder_level", "0"),
                "Reorder level",
            )
            cost_per_unit = self._parse_inventory_number(
                request.form.get("cost_per_unit", "0"),
                "Cost per unit",
            )
        except ValueError as error:
            flash(str(error), "danger")
            return redirect(url_for("manager.inventory"))

        db = Database()
        try:
            item = db.fetch_one("""
                SELECT current_stock
                FROM inventory_items
                WHERE id = %s AND active = 1
            """, (item_id,))

            if not item:
                flash("Inventory item not found.", "danger")
                return redirect(url_for("manager.inventory"))

            previous_stock = float(item["current_stock"] or 0)
            db.execute("""
                UPDATE inventory_items
                SET
                    name = %s,
                    unit = %s,
                    current_stock = %s,
                    reorder_level = %s,
                    cost_per_unit = %s,
                    supplier = %s,
                    notes = %s
                WHERE id = %s AND active = 1
            """, (
                name,
                unit,
                current_stock,
                reorder_level,
                cost_per_unit,
                supplier or None,
                notes or None,
                item_id,
            ))

            if current_stock != previous_stock:
                db.execute("""
                    INSERT INTO inventory_movements
                        (inventory_item_id, change_amount, stock_after, reason)
                    VALUES (%s, %s, %s, %s)
                """, (
                    item_id,
                    round(current_stock - previous_stock, 2),
                    current_stock,
                    "Stock updated from item editor",
                ))

            flash("Inventory item updated successfully.", "success")
        except Exception:
            flash("Unable to update inventory item. Check the values and try again.", "danger")
        finally:
            db.close()

        return redirect(url_for("manager.inventory"))

    def adjust_inventory(self, item_id):
        reason = request.form.get("reason", "Manual stock adjustment").strip()

        try:
            adjustment = float(request.form.get("adjustment", ""))
        except (TypeError, ValueError):
            flash("Stock adjustment must be a valid number.", "danger")
            return redirect(url_for("manager.inventory"))

        if adjustment == 0:
            flash("Stock adjustment cannot be zero.", "danger")
            return redirect(url_for("manager.inventory"))

        db = Database()
        try:
            item = db.fetch_one("""
                SELECT current_stock
                FROM inventory_items
                WHERE id = %s AND active = 1
            """, (item_id,))

            if not item:
                flash("Inventory item not found.", "danger")
                return redirect(url_for("manager.inventory"))

            current_stock = float(item["current_stock"] or 0)
            new_stock = round(current_stock + adjustment, 2)

            if new_stock < 0:
                flash("Stock cannot become negative.", "danger")
                return redirect(url_for("manager.inventory"))

            db.execute("""
                UPDATE inventory_items
                SET current_stock = %s
                WHERE id = %s AND active = 1
            """, (new_stock, item_id))
            db.execute("""
                INSERT INTO inventory_movements
                    (inventory_item_id, change_amount, stock_after, reason)
                VALUES (%s, %s, %s, %s)
            """, (
                item_id,
                round(adjustment, 2),
                new_stock,
                reason or "Manual stock adjustment",
            ))

            flash("Stock adjusted successfully.", "success")
        except Exception:
            flash("Unable to adjust stock. Please try again.", "danger")
        finally:
            db.close()

        return redirect(url_for("manager.inventory"))

    def archive_inventory_item(self, item_id):
        db = Database()
        try:
            db.execute("""
                UPDATE inventory_items
                SET active = 0
                WHERE id = %s
            """, (item_id,))
            flash("Inventory item archived successfully.", "success")
        except Exception:
            flash("Unable to archive inventory item.", "danger")
        finally:
            db.close()

        return redirect(url_for("manager.inventory"))

    # =========================================================
    # SALES
    # =========================================================

    def sales(self):

        db = Database()

        try:

            orders = db.fetch_all("""
                SELECT
                    orders.id,
                    orders.created_at,
                    orders.status,

                    restaurant_tables.name
                    AS table_name

                FROM orders

                LEFT JOIN restaurant_tables
                    ON orders.table_id =
                       restaurant_tables.id

                ORDER BY
                    orders.created_at DESC
            """)

            total_sales = 0

            for order in orders:

                order["items"] = db.fetch_all("""
                    SELECT
                        order_items.quantity,
                        order_items.price_at_order,
                        menu_items.name

                    FROM order_items

                    INNER JOIN menu_items
                        ON order_items.item_id =
                           menu_items.id

                    WHERE order_items.order_id = %s
                """, (
                    order["id"],
                ))

                order["total"] = 0

                for item in order["items"]:

                    order["total"] += (
                        float(
                            item["price_at_order"]
                        )
                        *
                        int(
                            item["quantity"]
                        )
                    )

                if order["status"] in [
                    "completed",
                    "delivered",
                    "paid",
                    "served"
                ]:

                    total_sales += order["total"]

        finally:
            db.close()

        return render_template(
            "manager/sales.html",
            orders=orders,
            total_sales=total_sales
        )

    # =========================================================
    # FILTER REPORTS
    # =========================================================

    def filter_reports(self):

        db = Database()

        start_date = (
            request.form.get("start_date")
            or request.args.get("start_date")
        )

        end_date = (
            request.form.get("end_date")
            or request.args.get("end_date")
        )

        status = (
            request.form.get("status")
            or request.args.get("status")
        )

        query = """
            SELECT
                orders.id,
                orders.created_at,
                orders.status,

                restaurant_tables.name
                AS table_name

            FROM orders

            LEFT JOIN restaurant_tables
                ON orders.table_id =
                   restaurant_tables.id

            WHERE 1 = 1
        """

        params = []

        if start_date:

            query += """
                AND DATE(orders.created_at) >= %s
            """

            params.append(
                start_date
            )

        if end_date:

            query += """
                AND DATE(orders.created_at) <= %s
            """

            params.append(
                end_date
            )

        if status and status != "all":

            query += """
                AND orders.status = %s
            """

            params.append(
                status
            )

        query += """
            ORDER BY
                orders.created_at DESC
        """

        try:

            orders = db.fetch_all(
                query,
                tuple(params)
            )

            total_sales = 0

            for order in orders:

                order["items"] = db.fetch_all("""
                    SELECT
                        order_items.quantity,
                        order_items.price_at_order,
                        menu_items.name

                    FROM order_items

                    INNER JOIN menu_items
                        ON order_items.item_id =
                           menu_items.id

                    WHERE order_items.order_id = %s
                """, (
                    order["id"],
                ))

                order["total"] = 0

                for item in order["items"]:

                    order["total"] += (
                        float(
                            item["price_at_order"]
                        )
                        *
                        int(
                            item["quantity"]
                        )
                    )

                if order["status"] in [
                    "completed",
                    "delivered",
                    "paid",
                    "served"
                ]:

                    total_sales += order["total"]

        finally:
            db.close()

        return render_template(
            "manager/sales.html",
            orders=orders,
            total_sales=total_sales,
            start_date=start_date,
            end_date=end_date,
            status=status
        )

    # =========================================================
    # VIEW ORDER
    # =========================================================

    def view_order(self, order_id):

        db = Database()

        try:

            order = db.fetch_one("""
                SELECT
                    orders.id,
                    orders.created_at,
                    orders.status,

                    restaurant_tables.name
                    AS table_name

                FROM orders

                LEFT JOIN restaurant_tables
                    ON orders.table_id =
                       restaurant_tables.id

                WHERE orders.id = %s
            """, (
                order_id,
            ))

            if not order:

                flash(
                    "Order not found.",
                    "danger"
                )

                return redirect(
                    url_for("manager.sales")
                )

            order["items"] = db.fetch_all("""
                SELECT
                    order_items.quantity,
                    order_items.price_at_order,
                    menu_items.name

                FROM order_items

                INNER JOIN menu_items
                    ON order_items.item_id =
                       menu_items.id

                WHERE order_items.order_id = %s
            """, (
                order_id,
            ))

            order["total"] = 0

            for item in order["items"]:

                order["total"] += (
                    float(
                        item["price_at_order"]
                    )
                    *
                    int(
                        item["quantity"]
                    )
                )

        finally:
            db.close()

        return render_template(
            "manager/view_order.html",
            order=order
        )