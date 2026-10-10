"""
services/config.py
------------------
Business-rule constants. Other services import these numbers - never type them again elsewhere.
(If Person A already created this file, just ADD these lines to it.)
"""

# ---------------------------------------------------------------- fair-price thresholds
# variance % = (price you paid - market price) / market price x 100
FAIR_GREAT_DEAL_MAX = -3      # variance <= -3 %          -> "Great deal"
FAIR_OK_MAX = 3               # -3 % < variance <= 3 %    -> "Fair"
FAIR_SLIGHTLY_HIGH_MAX = 8    # 3 % < variance <= 8 %     -> "Slightly high"; above 8 % -> "Overpaying"

# A purchase is compared with the latest market price on or before its date,
# but only if that price is at most this many days old.
REFERENCE_LOOKBACK_DAYS = 7

# ---------------------------------------------------------------- forecast thresholds
FORECAST_RISING_PCT = 3        # day-7 forecast at least +3 % above today's price  -> "Rising"
FORECAST_FALLING_PCT = -3      # day-7 forecast at most  -3 % below today's price  -> "Falling"
FORECAST_BAND_Z = 1.28         # 1.28 standard deviations = an 80 % confidence band
FORECAST_HISTORY_DAYS = 90     # days of past prices returned with a forecast

# ---------------------------------------------------------------- anomaly detection
ANOMALY_CONTAMINATION = 0.05       # Isolation Forest: expect about 5 % of purchases to be unusual
ANOMALY_STRONG_PCT = 25            # a deviation above 25 % is flagged on its own (no vote needed)
ANOMALY_HIGH_PCT = 30              # severity "high" above 30 %
ANOMALY_MEDIUM_PCT = 20            # severity "medium" above 20 %
ANOMALY_MIN_HISTORY = 5            # z-score needs at least 5 earlier purchases of the product
ANOMALY_IF_PER_PRODUCT_ROWS = 30   # Isolation Forest per product only if it has 30+ purchases
ANOMALY_Z_WINDOW_DAYS = 90         # z-score looks back 90 days
OVERPAYING_PCT = 8                 # supplier "overpaying" alert: last 3 purchases all more than 8 % above market

# ---------------------------------------------------------------- purchase decision engine
DECISION_STRONG_RISE_PCT = 6       # forecast rise of 6 % or more -> buy 20 % extra (prices may jump further)
DECISION_STRONG_RISE_MULT = 1.2
DECISION_STOCKOUT_LIMITED_MULT = 1.2   # when buying limited under stockout risk: lead-time need x 1.2
DECISION_LIMITED_FRACTION = 0.5    # "Buy Limited" = half of the shortfall
DECISION_FALLING_EXTRA_DAYS = 2    # wait for a falling price only if stock lasts lead time + 2 more days
DECISION_CHECK_FALLING_DAYS = 3    # "check again in 3 days" when waiting for a price drop
DECISION_CHECK_ENOUGH_DAYS = 5     # "check again in 5 days" when stock is already enough
DECISION_NO_SALES_COVER_MULT = 3   # no sales history: target stock = reorder level x 3
DECISION_CONFIDENCE_HIGH_MAPE = 3  # model error below 3 %  -> High confidence
DECISION_CONFIDENCE_MEDIUM_MAPE = 6  # below 6 % -> Medium, otherwise Low
SALES_WINDOW_DAYS = 30             # sales average window used by the engines
SUPPLIER_WINDOW_DAYS = 90          # "cheapest supplier" looks at the last 90 days of purchases

# ---------------------------------------------------------------- selling-price engine
PRICE_RANGE_LOW_FACTOR = 0.97      # recommended range: from 3 % below ...
PRICE_RANGE_HIGH_FACTOR = 1.05     # ... to 5 % above the recommended price
PRICE_VS_MARKET_WARN_PCT = 8       # warn when the current selling price is more than 8 % away from the market
RETAIL_FROM_WHOLESALE = 1.12       # retail = wholesale x 1.12 when no retail price is known
COST_BASIS_PURCHASES = 5           # cost basis = weighted average of the last 5 purchases
