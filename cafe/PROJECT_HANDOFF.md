# Himalayan Bites Restaurant Management System

This folder is a replacement-ready copy of the existing Flask restaurant management project. It includes the completed customer dashboard, receptionist dashboard and order operations, manager dashboard, menu management, reports, QR table management, inventory management, authentication pages, and their corresponding route/controller updates.

## Before running

Create a virtual environment, install the dependencies from `requirements.txt`, and provide the variables in `.env.example` through your deployment platform or shell environment. Never commit real passwords, database credentials, or production secret keys.

The database initialization workflow in `app/modules/database.py` must be run against the target MySQL database before first use. It creates the existing restaurant tables plus the inventory tables, inventory movement log, order-number migration, and receptionist-note migration.

All manager pages now use `app/templates/partials/manager_sidebar.html` for one shared navigation and one active-page system. The manager dashboard, menu, order history, reports, table QR, and inventory pages use the same sidebar links, including Table QR codes and Inventory, with a consistent 258px desktop offset and responsive content gutters.

The customer dashboard is optimized for QR scanning on mobile phones. It uses a simple single-column menu, large touch targets, horizontal category chips, quick search, and a compact cart bar. The page reserves bottom space for the cart bar, so it does not cover the last food cards or block menu actions. The full cart opens as a focused bottom sheet only when the customer chooses to review the order.

The final dashboard polish layer is loaded from `app/static/css/dashboard-polish.css`. It gives the manager and receptionist workspaces a hospitality control-room theme: warm parchment surfaces, charcoal navigation, terracotta action accents, sage service states, restaurant-style display typography, clearer operational cards, and consistent staff spacing. It also adds restrained rise-in motion, stable hover/pressed states, 44px controls, and reduced-motion support. The manager history screen now uses the shared manager navigation, and receptionist history is included in the same theme family. The dashboard shell is applied through `app/templates/base.html`.

## Main routes

| Role | Route | Purpose |
|---|---|---|
| Customer | `/customer/` or `/customer/qr/<table_id>` | QR table entry |
| Customer | `/customer/dashboard` | Customer menu and ordering dashboard |
| Receptionist | `/receptionist/dashboard` | Reception workstation |
| Receptionist | `/receptionist/orders` | Order operations, status changes, notes, payment, and table clearing |
| Manager | `/manager/dashboard` | Manager overview |
| Manager | `/manager/menu` | Menu CRUD and availability |
| Manager | `/manager/reports` | Cleared-order sales reports |
| Manager | `/manager/table-qr` | Table QR code management |
| Manager | `/manager/inventory` | Inventory and manual stock management |

## Important limitations before production sale

The reports page intentionally does not present profit because the database does not yet store food cost, labor, rent, tax, or other expenses. The inventory page currently supports manual stock adjustments but does not automatically deduct ingredients from orders because recipe-to-ingredient mapping is not yet implemented. Review CSRF protection, production session settings, default credentials, and the customer checkout price calculation before using the system with real customer data or payments.
