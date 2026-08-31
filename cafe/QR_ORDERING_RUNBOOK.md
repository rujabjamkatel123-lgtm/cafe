# Restaurant QR Table Ordering Refactor

## What changed

The customer ordering flow is now public and session-based. `GET /customer?table=3`, `GET /customer/table/3`, and `GET /table/3` open the customer menu and bind the selected table to the Flask session. Cart mutations and order placement use that session table, so a guest browser can add items, remove items, and place an order without authentication. Guest orders are inserted with `user_id = NULL`, `table_id` set to the scanned table, and `status = 'Placed'`.

The customer header displays a prominent `📍 Table X` badge. The same table session can submit multiple separate orders; every submission gets its own order number and appears separately in customer history and the receptionist queue. A successful order marks the table `occupied`. Reception must finish or cancel all active orders and click **Clear Table** before the table becomes `available` again. After the table is cleared, refreshing the customer dashboard starts a new order cycle.

Receptionist and manager blueprints remain protected by their role decorators. Unauthenticated requests redirect to `/login`. The receptionist dashboard now loads order items and totals, counts both legacy `pending` and new `Placed` orders, and labels incoming cards as `New Order from Table X`.

The manager dashboard now includes five QR cards. Each QR payload points directly to `/customer?table=1` through `/customer?table=5`. Each card supports PNG download, and the print button opens a printable QR page. The seven-day sales chart, manager order history, and reports use database aggregates rather than placeholder values. Sales and profit metrics count only orders settled by reception through **Clear Table**; customer and staff history still preserve the individual orders. Protected endpoints are `/manager/qr/<table_id>` and `/manager/qr/<table_id>/download`.

Local HTTP sessions are enabled by default. Set `SECURE_SESSION_COOKIE=1` when deploying behind HTTPS.

## Local setup

From the `Restaurant` directory, create and activate a virtual environment, install dependencies, set the database variables, initialize the schema, and start Flask:

```bash
cd Restaurant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY='replace-with-a-long-random-value'
export MYSQL_HOST='127.0.0.1'
export MYSQL_PORT='3306'
export MYSQL_USER='restaurant_user'
export MYSQL_PASSWORD='restaurant_password'
export MYSQL_DATABASE='restaurant'
export SECURE_SESSION_COOKIE='0'  # use 1 only behind HTTPS

python3 -c "from app.modules.database import Database; Database.create_tables()"
python3 run.py
```

Open `http://127.0.0.1:5000/customer?table=3` to test the guest flow. Staff users should use `/login`; after authentication, the receptionist dashboard is `/receptionist/dashboard` and the manager dashboard is `/manager/dashboard`.

## Verification

The repository includes `verify_routes.py`. Run:

```bash
python3 -m compileall -q app run.py verify_routes.py
python3 verify_routes.py
```

The route assertions, unauthenticated receptionist redirect, manager QR PNG response, and invalid QR table rejection pass without requiring a live database. The customer request smoke check requires a configured MySQL database to complete the menu/order flow.

## Operational notes

The current database helper uses MySQL transactions and the existing schema already allows guest orders through nullable `orders.user_id`. If an existing deployment uses lowercase statuses, the receptionist feed accepts both `Placed` and legacy `pending`; new customer orders consistently use the required `Placed` value.
