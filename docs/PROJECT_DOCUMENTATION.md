# Stable Supermarket Inventory Management System

## 1. Project overview

Stable Supermarket Inventory Management System is a desktop application designed to help a supermarket manage products, stock, sales, suppliers, customers, and staff access from one place. It replaces manual stock records with a MySQL-backed system that keeps an audit trail of inventory changes.

The project follows the original proposal: a professional Python desktop application using CustomTkinter for the interface and MySQL/MariaDB for persistent data storage.

## 2. Technology stack

| Technology | Purpose |
| --- | --- |
| Python 3 | Application logic |
| CustomTkinter | Modern desktop user interface |
| MySQL/MariaDB via XAMPP | Database server |
| mysql-connector-python | Secure database connection |
| bcrypt | Password hashing |
| python-dotenv | Private database configuration |
| PyInstaller | Local Windows executable build |

## 3. Implemented features

### Authentication and roles

- Login with bcrypt-hashed passwords.
- First-run administrator account creation.
- Optional **Remember me for 30 days** session on the local computer.
- Administrator and Staff account roles.
- Administrators can create and update user accounts.
- Staff can view products, make sales, and view sales history. Administrative management pages are restricted.

### Product and inventory management

- Create, update, and delete products.
- Each product has a unique SKU, name, quantity, reorder level, price, category, and supplier.
- Product forms provide sensible defaults for empty quantity, reorder level, and price fields.
- Low-stock products are highlighted when their quantity is at or below the reorder level.
- Categories and suppliers can be selected from drop-down lists when products are created or edited.

### Sales management

- Add multiple products to one sale using a cart.
- Add a product by choosing it from a drop-down, typing a product name, or entering its SKU directly.
- Select a named customer or use **Walk-in Customer**.
- Cart displays quantity, unit price, line totals, and the full sale total.
- Remove products from the cart before checkout.
- Checkout verifies stock again inside a database transaction before recording the sale.
- Every sale deducts product stock and creates an inventory-log entry.

### Sales history and receipts

- View completed sales with customer, cashier, total, and date.
- Filter sales by date using `YYYY-MM-DD`.
- Open a selected sale to see every item.
- Generate a local text receipt for a selected sale. Receipts are stored in the ignored `receipts/` folder.

### Stock adjustments and reporting

- Restock products through a dedicated screen.
- Record damaged or missing stock without allowing negative quantities.
- Record an optional reason for each adjustment.
- Store adjustments in `inventory_log` for traceability.
- Dashboard shows product count, units in stock, low-stock count, and today's sales total.
- Reports page shows recent inventory activity.

### Backup and distribution

- Administrators can create dated SQL backups from the **Database Backup** page.
- Backups are stored in the ignored `backups/` folder.
- A local Windows executable can be built with PyInstaller at `dist/StableSupermarket.exe`.

## 4. Database design

| Table | Purpose |
| --- | --- |
| `users` | Administrator and Staff login accounts |
| `user_sessions` | Time-limited remembered-login sessions |
| `categories` | Product classifications |
| `suppliers` | Supplier contact records |
| `customers` | Customer contact records |
| `products` | Product SKU, price, stock level, supplier, and category |
| `sales` | Completed sale header, customer, cashier, total, and date |
| `sale_items` | Individual products included in each sale |
| `inventory_log` | Stock movement audit trail |

Key relationships:

```text
Category  ──< Products >── Supplier
Customer  ──< Sales >───── User (cashier)
Sales     ──< Sale Items >─ Products
Products  ──< Inventory Log
```

## 5. Application workflow

1. Start MySQL in XAMPP.
2. Sign in as an Administrator or Staff member.
3. An Administrator creates categories, suppliers, and products.
4. Staff or Administrators open **New Sale**.
5. Add products to the cart, select a customer if needed, and complete the sale.
6. The system saves the sale, deducts stock, and records the stock movement.
7. Use **Sales History** to review sales or create receipts.
8. Use **Stock Adjustment** to restock goods or record damaged/missing items.

## 6. Local setup guide

### Database

1. Open XAMPP Control Panel and start MySQL.
2. Open phpMyAdmin from the MySQL **Admin** button.
3. Import `database/schema.sql`.
4. Copy `.env.example` to `.env`.
5. For a standard XAMPP setup, use:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=inventory_management
DB_USER=root
DB_PASSWORD=
```

Use your real MySQL password if you created one.

### Run from source

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### Run the executable

1. Start XAMPP MySQL.
2. Keep `.env` in the `dist` folder beside `StableSupermarket.exe`.
3. Open `dist/StableSupermarket.exe`.

## 7. Backup and restore

### Create a backup

1. Sign in as an Administrator.
2. Open **Database Backup**.
3. Click **Create database backup**.
4. Copy the generated file from `backups/` to a safe location.

### Restore a backup

1. Open phpMyAdmin.
2. Select the `inventory_management` database.
3. Use the **Import** tab to select the saved `.sql` backup file.

## 8. GitHub publishing guide

You can push this repository yourself. Before pushing, confirm that `.env` is not listed by `git status`.

```powershell
git add .
git commit -m "Build Stable Supermarket inventory management system"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

Do not upload:

- `.env` or `dist/.env`
- `.venv/`
- `backups/`
- `receipts/`
- `build/` or `dist/`

These files are excluded by `.gitignore`.

## 9. Future improvements

- Barcode scanner support
- Printable PDF receipts
- Sales return/refund process
- Product image support
- More advanced reports and charts
- Cloud backup and multi-branch support
- Web or mobile companion application

## 10. Project status

The core inventory, sales, stock-control, reporting, authentication, backup, and user-role requirements are implemented and ready for local use with XAMPP.
