# VyapariAI - Shopkeeper's Manual

VyapariAI helps you answer four daily questions: **Am I paying a fair price? Will the price go up? How much should I buy? What should I sell at?**
You type in what you buy and sell. The app compares your prices with the market and gives simple advice. You decide; the app only helps.

---
## Your first day (10 steps)
1. **Sign up** with your name, e-mail and a password (at least 6 characters).
2. **Set up your shop**: shop name, type and city. Press Continue.
3. Open **Products** and press **Add Product**. Add 5 to 10 things you sell. Give each a **unit** (kg, litre, packet), the **stock you have today** and a **reorder level** (the stock at which you usually order again).
4. In the same window choose the **Reference commodity** (for example Rice) so the app can compare with the market price. [screenshot: add_product.png]
5. Open **Suppliers** and add the people you buy from. Tick the products each one sells.
6. Open **Purchases** and record what you bought recently: product, supplier, quantity, price **per kg/litre/packet** and date.
7. Open **Sales** and record what you sold. Do this every day; it takes one minute.
8. Open the **Dashboard**. Read the green box "What to buy" and the alerts.
9. Open **Pricing** to see if you paid a fair price, and **Recommendations** to see how much to buy.
10. Press the round orange button at the bottom right and **ask the AI advisor** a question in English, Hindi or Marathi.

> Tip: if you already keep your records in Excel, use **Import CSV** on the Products, Purchases and Sales pages.

---
## Dashboard
**What it is:** a one-screen summary of your shop. [screenshot: dashboard.png]
**When to use:** every morning.
**Steps:** look at the four boxes (products, this month's purchases, stock value, alerts). Read **What to buy**, **Low stock** and **Latest alerts**. Use the product list above the chart to see the market price, the forecast and the prices you paid.
**Tips:** the first-time checklist disappears when you have added products, suppliers, purchases and sales.

## Products
**What it is:** the list of things you sell and how much stock you have. [screenshot: products.png]
**Steps:** *Add Product* to create. The pencil edits, the dustbin deletes. Use search and the category box to find products. *Import CSV* adds many products at once.
**Tips:** stock changes by itself when you record purchases and sales. You cannot delete a product that already has purchases or sales.

## Suppliers
**What it is:** the people you buy from. [screenshot: suppliers.png]
**Steps:** *Add Supplier*, tick the products they sell. Open the **Compare** tab, choose a product and see every supplier's average price, how steady the price is, and the **Best value** badge. Click a supplier to see their prices over time.
**Tips:** "Best value" means the lowest average price among suppliers with at least 3 orders whose price does not jump around.

## Purchases
**What it is:** where you record every purchase. [screenshot: purchases.png]
**Steps:** choose product and supplier, type quantity and **price per unit**, check the date, press *Save Purchase*. While you type the price, a small tag tells you if it is fair. If the price looks unusual you will see a window: keep it if it is correct, or **Undo** if you typed it wrongly.
**Tips:** use the **History** tab to filter, sort and delete old purchases.

## Sales
**What it is:** where you record what you sold. Stock goes down automatically. [screenshot: sales.png]
**Steps:** choose product, quantity (the price is filled in), press *Save Sale* or Enter. The window stays open for the next sale. The right side shows today's sales and the last 30 days.
**Tips:** the app cannot sell more than you have in stock. Daily sales make the advice about quantities much better.

## Inventory
**What it is:** your stock now. [screenshot: inventory.png]
**Steps:** read the status, the days of stock left and the last purchase. Rows in red need action: press **Record purchase**.

## Pricing (Price Analysis)
**What it is:** did you pay a fair price compared with the market? [screenshot: price_analysis.png]
**Steps:** choose a product. The dots are your purchases (one colour per supplier), the dashed line is the market price. Read the verdict and the **Potential savings** (money you could have saved by paying the market price).
**Tips:** press **Explain with AI** to hear the answer in your language.

## Forecast
**What it is:** where the market price is expected to go in the next 7 or 14 days. [screenshot: forecast.png]
**Steps:** choose a product and 7 or 14 days. The shaded area is the likely range. The right side shows how accurate the model was in the past.
**Tips:** a forecast is an estimate. Use it as one more hint, not as a promise.

## Alerts
**What it is:** warnings that need your attention. [screenshot: alerts.png]
**Steps:** *Scan now* checks all your purchases. Filter by unread, severity and type. *Mark as read* when you have dealt with it.

## Recommendations
**What it is:** advice on **what to buy** and **what to sell at**. [screenshot: recommendations.png]
**Steps:** the first tab lists every product, most urgent first, with the reasons. The second tab shows a selling price range; move the **Target margin** slider to see what happens with a different profit.

## AI Advisor
**What it is:** a chat assistant that knows your shop's numbers. [screenshot: advisor.png]
**Steps:** choose **EN / HI / MR**, type a question or press the **microphone** and speak (Chrome or Edge). Press the **speaker** icon to hear the answer. Open **Sources used** to see the exact numbers behind the answer.
**Tips:** if the AI is offline you still get a short "Basic answer" with the key numbers.

## Settings
**What it is:** your shop details and the rules the advice uses. [screenshot: settings.png]
**Steps:** change the target and minimum profit margin, supplier delivery time, how many days of stock you want to keep, and how sensitive the price alerts are. You can also change your password here.

---
## How to read the advice

### Buy Now / Buy Limited Quantity / Wait
| Advice | Meaning | What to do |
|---|---|---|
| **Buy Now** | Your stock will run out before new stock can arrive, or the price is expected to rise and your stock is low. | Order the quantity shown. |
| **Buy Limited** | You need some stock, but the price is bad, or you are only a little below your target. | Order only the small quantity shown and compare suppliers. |
| **Wait** | You have enough stock, or the price is expected to fall. | Check again after the number of days shown. |

### Fair-price verdicts (how your price compares with the market)
| Verdict | Your price compared with the market |
|---|---|
| **Great deal** | 3 % or more **below** the market |
| **Fair** | between 3 % below and 3 % above |
| **Slightly high** | 3 % to 8 % above |
| **Overpaying** | more than 8 % above |

### Alert severity
| Colour | Meaning |
|---|---|
| **High** (red) | Price is more than 30 % away from normal, or all three checks agree. Check this first. |
| **Medium** (yellow) | Price is 20 to 30 % away, or two checks agree. |
| **Low** | Small difference. Good to know. |

### Forecast confidence
| Label | Meaning |
|---|---|
| **High** | The model's average mistake in past tests was under 3 %. |
| **Medium** | Between 3 % and 6 %. |
| **Low** | 6 % or more, or no accuracy information yet. Treat the forecast as a rough hint. |

> The app gives **estimates to help you decide**. It cannot know about sudden events such as floods or new government rules. The final decision is always yours.
