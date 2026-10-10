# Manual bug-bash checklist (Track A pages)

How to use: log in as a **new** user (not the demo user) so you can break things freely. Do every step, write **Pass** or **Fail + what you saw** in the last column.
A step passes only if the *Expected result* happens AND nothing crashes (no blank page, no browser console error, no "Internal Server Error").
Automated tests cover the API; this list covers what only a human sees (layout, messages, double clicks).

| Page | Step | Expected result | Pass? |
|---|---|---|---|
| **Login** | Leave both fields empty and press Login | Message asks for e-mail and password; no request is sent | |
| Login | Wrong password for an existing e-mail | "Invalid email or password." (same text for an unknown e-mail) | |
| Login | Type the e-mail in capital letters (`DEMO@VYAPARIAI.COM`) | Login works (e-mails are not case sensitive) | |
| Login | Press Enter in the password field | Same as clicking Login | |
| Login | Double-click Login quickly | Only one login happens, no error | |
| Login | Stop the backend, then log in | Clear message "Cannot reach the server", no blank page | |
| Login | Log in, then open `/login` directly | You are sent to the dashboard | |
| Login | Open `/dashboard` while logged out | You are sent to `/login` | |
| Login | Delete the token in browser storage, press F5 on a page | Sent to `/login`, no crash | |
| Login | Wait for the token to expire (or edit it) then click any menu item | "Session expired, please log in again." on the login page | |
| **Signup** | Password with 3 characters | Error about the minimum length | |
| Signup | Invalid e-mail (`abc`) | Error under the field | |
| Signup | Sign up with an e-mail that exists | "An account with this email already exists." | |
| Signup | Name of 200 characters | Rejected or shortened with a clear message, no crash | |
| Signup | Password and repeat password differ | Error, nothing is created | |
| Signup | Double-click the button | One account only | |
| Signup | After success | You land on Shop Setup (not the dashboard) | |
| Signup | Browser back button after signup | No second account is created; no crash | |
| **Shop Setup** | Submit with empty fields | Message "fill in all fields" | |
| Shop Setup | Shop name of 150 characters | Clear error or accepted up to the limit, no crash | |
| Shop Setup | Double-click Continue | Only one shop is created (no 409 error shown to you) | |
| Shop Setup | Open `/dashboard` before finishing setup | You are sent back to `/shop-setup` | |
| Shop Setup | Finish setup, press the browser back button | You do not see Shop Setup again with an empty form creating a second shop | |
| Shop Setup | Reload the page after saving | You go to the dashboard | |
| **Products** | Add a product with only a name and a unit | Saved; shows in the table as **Out of Stock** (stock 0) | |
| Products | Opening stock `-5` | Rejected (cannot be negative) | |
| Products | Opening stock `0`, reorder level `10` | Status "Out of Stock"; with stock 10 it shows "Low Stock"; with 11 "In Stock" | |
| Products | Opening stock `1000000000000` | Rejected or shown without breaking the table layout | |
| Products | Name of 120 characters, then 121 | 120 saved and wrapped nicely; 121 rejected | |
| Products | Name `<script>alert(1)</script>` | Shown as plain text, no popup | |
| Products | Add the same name twice (also `rice` and `RICE`) | "A product with this name already exists" | |
| Products | Double-click Add Product | Only one product is created | |
| Products | Link a reference commodity, then edit and remove it | Both saves work; fair price and forecast pages react | |
| Products | Delete a product that has a purchase | "Product has purchases or sales and cannot be deleted" (toast), product stays | |
| Products | Delete a product with no purchases | Confirmation, then it disappears from the list and from Inventory | |
| Products | Search `' OR 1=1 --` | No results, no error | |
| **Suppliers** | Add a supplier with only a name | Saved; "Not linked yet" in the products column | |
| Suppliers | Link 3 products, edit, unlink one | The list updates correctly | |
| Suppliers | Phone number with letters | Accepted as text or rejected consistently (note which) | |
| Suppliers | Add the same name twice (`abc`, `ABC`) | "A supplier with this name already exists" | |
| Suppliers | Delete a supplier that has purchases | "Supplier has purchases and cannot be deleted" | |
| Suppliers | Compare tab with a product that has no purchases | "No purchases ... nothing to compare yet", no chart error | |
| Suppliers | Compare tab: click a supplier row | Price-over-time chart appears for that supplier | |
| Suppliers | Name of 200 characters | Rejected or wrapped, layout intact | |
| Suppliers | Double-click Save in the edit window | One update, no duplicate | |
| **Purchases** | Quantity `0`, `-3`, empty | Error under the field, nothing saved | |
| Purchases | Price `0` or `-1` | Error under the field | |
| Purchases | Date tomorrow | Rejected: "Date cannot be in the future" | |
| Purchases | Quantity `1e9`, price `99999999999` | Rejected or saved without breaking the totals/layout | |
| Purchases | Type a price 40 % above the market | Live chip shows "Overpaying"; after saving, the "This price looks unusual" window opens | |
| Purchases | In that window click "Undo" | Purchase disappears, stock goes back, alert badge decreases | |
| Purchases | Double-click Save Purchase | Only ONE purchase appears in the list | |
| Purchases | Save with the server stopped | Error toast; the form keeps your values | |
| Purchases | History tab: filter by product, dates, sort by price, next page | Counts and pages are correct | |
| Purchases | Delete a purchase whose stock was already sold | Error explains how much was sold; nothing changes | |
| Purchases | Import CSV: dry run on `docs/samples/purchases_with_5_errors.csv` | 5 errors with row numbers; nothing saved until you fix them | |
| **Sales** | Quantity larger than the stock | "Only X kg in stock" and stock unchanged; the form shows the shortage while typing | |
| Sales | Product without a selling price, empty price field | Error under the price field | |
| Sales | Quantity `0` or `-1` | Error | |
| Sales | Date in the future | Error | |
| Sales | Save, then save again with Enter | Two separate sales; form stays open | |
| Sales | Delete a sale | Stock is restored; today's list updates | |
| Sales | Choose a product, then another | Price field is prefilled with that product's price | |
| Sales | Last 30 days table with no sales | "No sales in the last 30 days." | |
| Sales | Import CSV with a sale that would make stock negative | Error names the row and the available stock | |
| **Inventory** | Product with stock below the reorder level | Row highlighted, "Low Stock", "Record purchase" button opens Purchases with the product selected | |
| Inventory | Product without sales | Days of cover shows `-` (not 0 or NaN) | |
| Inventory | Search and category filter together | Counts update ("x of y products") | |
| Inventory | Product with a very long name | Row layout intact | |
| Inventory | Record a purchase, return to Inventory | Stock and last purchase updated without a reload | |
| Inventory | Empty shop | "No products yet. Add products first." | |
| Inventory | Stock value card | Equals the sum of stock x last purchase price (check one product by hand) | |
| Inventory | Backend stopped | Error box with Retry, no blank page | |
| Inventory | Days of cover colours | Red below the supplier delivery time, amber below 7 days | |
| **Alerts** | New user with no data | "No alerts - your purchase prices look normal" | |
| Alerts | Click "Scan now" twice | Second scan says "nothing new"; no duplicate alerts | |
| Alerts | Mark one alert read | Blue dot disappears; sidebar badge decreases by 1 | |
| Alerts | Mark all read | Badge disappears | |
| Alerts | Combine filters Unread + High + Price anomaly | List matches all three filters | |
| Alerts | "View price analysis" on an alert | Opens Price Analysis with that product selected | |
| Alerts | Low stock alert, then restock and scan | The low-stock alert is closed (marked read) | |
| Alerts | Open the page with the server stopped | Error box with Retry | |
| Alerts | 100+ alerts (import many purchases) | Page stays fast and scrolls | |
| Alerts | Badge in sidebar and bell in top bar | Same number | |
| **Settings** | Target margin `150` | Error "Must be between 0 and 100" before saving | |
| Settings | Minimum margin higher than target | Error: minimum cannot be higher than the target | |
| Settings | Lead time `31`, cover days `0`, z-score `5`, alert limit `4` | Each shows its own range error | |
| Settings | Empty number field | "Enter a number" | |
| Settings | Change cover days to 30, save, open Recommendations | Quantities change (target stock = 30 days of sales) | |
| Settings | Change language to Marathi, open the Advisor | The Advisor opens in Marathi | |
| Settings | Wrong current password | "Your current password is not correct." | |
| Settings | New password = old password | Rejected with a clear message | |
| Settings | Change password, log out, log in with the new one | Works; the old one fails | |
| Settings | Double-click Save settings | One save, one "Settings saved" message | |
