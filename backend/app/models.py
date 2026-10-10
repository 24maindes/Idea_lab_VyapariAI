"""
models.py - all 11 database tables of VyapariAI (SQLAlchemy 2.0, declarative "Column" style).

Rules used everywhere:
  * every table that belongs to a shop has shop_id (a shop must never see another shop's rows)
  * columns are snake_case; money is Float in rupees; "price" means PRICE PER UNIT
  * indexes on shop_id / product_id / date columns because we filter and sort on them all the time
"""
from sqlalchemy import (Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String,
                        Table, Text, UniqueConstraint, func)
from sqlalchemy.orm import relationship

from app.database import Base


# ====================================================================== 1. User (the original table, unchanged)
class User(Base):
    """Users table (login / signup). One user owns one shop."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shop = relationship("Shop", back_populates="user", uselist=False)   # one user -> one shop


# ====================================================================== 2. Shop
class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)   # unique = one shop per user
    shop_name = Column(String, nullable=False)
    shop_type = Column(String, nullable=True)
    location = Column(String, nullable=True)

    # business settings (the shopkeeper can change them in Settings; services read them)
    target_margin_pct = Column(Float, nullable=False, default=15)        # margin we aim for when suggesting a selling price
    min_margin_pct = Column(Float, nullable=False, default=5)            # never suggest a price with less margin than this
    lead_time_days = Column(Integer, nullable=False, default=3)          # days a supplier takes to deliver
    cover_days = Column(Integer, nullable=False, default=14)             # how many days of stock we want to hold
    anomaly_threshold_pct = Column(Float, nullable=False, default=15)    # % away from normal that counts as abnormal
    z_cutoff = Column(Float, nullable=False, default=2.5)                # z-score above which a price is abnormal
    language = Column(String, nullable=False, default="en")              # en / hi / mr (AI advisor language)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="shop")
    products = relationship("Product", back_populates="shop", cascade="all, delete-orphan")
    suppliers = relationship("Supplier", back_populates="shop", cascade="all, delete-orphan")
    purchases = relationship("Purchase", back_populates="shop", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="shop", cascade="all, delete-orphan")


# ====================================================================== association: which supplier sells which product
supplier_products = Table(
    "supplier_products",
    Base.metadata,
    Column("supplier_id", Integer, ForeignKey("suppliers.id"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
)


# ====================================================================== 3. Product
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    unit = Column(String, nullable=False, default="kg")                  # kg / litre / packet
    current_stock = Column(Float, nullable=False, default=0)
    reorder_level = Column(Float, nullable=False, default=0)
    selling_price = Column(Float, nullable=True)                         # Rs per unit
    reference_commodity = Column(String, nullable=True)                  # links to reference_prices.commodity
    created_at = Column(DateTime, server_default=func.now())

    shop = relationship("Shop", back_populates="products")
    purchases = relationship("Purchase", back_populates="product")
    sales = relationship("Sale", back_populates="product")
    suppliers = relationship("Supplier", secondary=supplier_products, back_populates="products")


# ====================================================================== 4. Supplier
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    contact = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    shop = relationship("Shop", back_populates="suppliers")
    purchases = relationship("Purchase", back_populates="supplier")
    products = relationship("Product", secondary=supplier_products, back_populates="suppliers")


# ====================================================================== 5. Purchase
class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)                           # Rs PER UNIT
    purchase_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    shop = relationship("Shop", back_populates="purchases")
    product = relationship("Product", back_populates="purchases")
    supplier = relationship("Supplier", back_populates="purchases")


# ====================================================================== 6. Sale
class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)                           # Rs PER UNIT
    sale_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    shop = relationship("Shop", back_populates="sales")
    product = relationship("Product", back_populates="sales")


# ====================================================================== 7. ReferencePrice (public market data, NO shop_id)
class ReferencePrice(Base):
    __tablename__ = "reference_prices"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String, nullable=False)
    market = Column(String, nullable=True)
    price_date = Column(Date, nullable=False)
    wholesale_price = Column(Float, nullable=False)
    retail_price = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    source = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_reference_commodity_date", "commodity", "price_date"),
        UniqueConstraint("commodity", "market", "price_date", name="uq_reference_commodity_market_date"),   # one price per commodity, market and day
    )


# ====================================================================== 8. Alert
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=True)
    alert_type = Column(String, nullable=False)       # e.g. price_anomaly, low_stock
    severity = Column(String, nullable=True)          # low / medium / high
    message = Column(Text, nullable=True)
    methods = Column(String, nullable=True)           # which detectors fired, e.g. "zscore,isolation_forest"
    score = Column(Float, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())


# ====================================================================== 9. ActivityLog
class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    kind = Column(String, nullable=True)
    text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# ====================================================================== 10. AdvisorMessage
class AdvisorMessage(Base):
    __tablename__ = "advisor_messages"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    role = Column(String, nullable=False)             # user / assistant
    content = Column(Text, nullable=False)
    language = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# ====================================================================== 11. ModelMetric (global: one row per commodity per model)
class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String, nullable=False, index=True)
    model_name = Column(String, nullable=False)
    mape = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    is_best = Column(Boolean, nullable=False, default=False)
    horizon_days = Column(Integer, nullable=True)
    trained_at = Column(DateTime, server_default=func.now())
