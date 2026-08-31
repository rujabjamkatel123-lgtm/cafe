# Targeted changes only

This corrected copy preserves the original project files. Only the following files were changed or added for the QR table-ordering, settlement, reporting, and cart-interaction fixes:

- `app/__init__.py` — public table entry, local session-cookie behavior, and eight-hour session lifetime.
- `app/controllers/auth.py` — persistent authenticated sessions and staff redirects.
- `app/controllers/auth.py` — query-parameter table binding, multiple orders, per-table numbering, occupied-table updates, and `Placed` guest orders.
- `app/controllers/manager.py` — QR image generation, real settled-sales chart, reports, order-history totals, and safe menu archiving.
- `app/controllers/receptionist.py` — replaced with the user-supplied receptionist controller, with only route/schema compatibility preserved.
- `app/routes/auth.py` — removed legacy login-protected customer route collisions.
- `app/routes/customer.py` — public customer and `/customer/table/X` routes plus live status endpoint.
- `app/routes/manager.py` — protected manager QR endpoints.
- `app/templates/customer/dashboard.html` — `📍 Table X` badge, per-table order labels, no-refresh cart actions, live status polling, and animated design.
- `app/templates/manager/dashboard.html` — QR preview/download/print card and real sales chart.
- `app/templates/receptionist/dashboard.html` — table-specific incoming-order labels, occupied/available status, and Clear Table action.
- `app/templates/receptionist/orders.html` — replaced with the user-supplied receptionist orders template.
- `app/templates/receptionist/history.html` — finished-order history cards with detail popups.
- `app/modules/database.py` — idempotent per-table order-number migration and Starter category migration.
- `app/modules/order.py` — aligned order-model status helpers.
- `app/modules/menu.py` — safe archive behavior for referenced menu items.
- `app/templates/manager/menu.html` — custom archive confirmation modal.
- `app/templates/manager/history.html` — per-table order labels and current manager filter links.
- `config.py` — configurable secure session cookie setting.
- `requirements.txt` — QR generation dependency.
- `verify_routes.py` — verification smoke tests.
- `QR_ORDERING_RUNBOOK.md` — setup and run instructions.

All other source files and assets are preserved from the original repository without modification.
