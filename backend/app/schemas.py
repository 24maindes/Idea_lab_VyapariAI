import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from pydantic.alias_generators import to_camel

class SignupRequest(BaseModel):
    fullName: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    fullName: str
    email: EmailStr

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# =====================================================================
# Shop schemas (JSON keys are camelCase, Python attributes are snake_case)
# =====================================================================
class CamelModel(BaseModel):
    """Base class: Python uses snake_case, the JSON API uses camelCase (shopName, targetMarginPct ...)."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


Language = Literal["en", "hi", "mr"]


class ShopCreate(CamelModel):
    shop_name: str = Field(min_length=1, max_length=120)
    shop_type: str | None = None
    location: str | None = None
    target_margin_pct: float = Field(15, ge=0, le=100)
    min_margin_pct: float = Field(5, ge=0, le=100)
    lead_time_days: int = Field(3, ge=0, le=30)
    cover_days: int = Field(14, ge=1, le=90)
    anomaly_threshold_pct: float = Field(15, ge=5, le=50)
    z_cutoff: float = Field(2.5, ge=1.5, le=4)
    language: Language = "en"

    @model_validator(mode="after")
    def margins_make_sense(self):
        if self.min_margin_pct > self.target_margin_pct:
            raise ValueError("minMarginPct cannot be higher than targetMarginPct")
        return self


class ShopUpdate(CamelModel):
    """Every field optional: send only what changed."""
    shop_name: str | None = Field(None, min_length=1, max_length=120)
    shop_type: str | None = None
    location: str | None = None
    target_margin_pct: float | None = Field(None, ge=0, le=100)
    min_margin_pct: float | None = Field(None, ge=0, le=100)
    lead_time_days: int | None = Field(None, ge=0, le=30)
    cover_days: int | None = Field(None, ge=1, le=90)
    anomaly_threshold_pct: float | None = Field(None, ge=5, le=50)
    z_cutoff: float | None = Field(None, ge=1.5, le=4)
    language: Language | None = None


class ShopOut(CamelModel):
    id: int
    user_id: int
    shop_name: str
    shop_type: str | None = None
    location: str | None = None
    target_margin_pct: float
    min_margin_pct: float
    lead_time_days: int
    cover_days: int
    anomaly_threshold_pct: float
    z_cutoff: float
    language: str
    created_at: dt.datetime | None = None


# =====================================================================
# Products
# =====================================================================
Unit = Literal["kg", "litre", "packet", "box"]


class ProductCreate(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    category: str | None = Field(None, max_length=60)
    unit: Unit = "kg"
    opening_stock: float = Field(0, ge=0)                      # becomes current_stock
    reorder_level: float = Field(0, ge=0)
    selling_price: float | None = Field(None, gt=0)
    reference_commodity: str | None = None


class ProductUpdate(CamelModel):
    """All optional: send only what changed. Stock is changed by purchases and sales, not here."""
    name: str | None = Field(None, min_length=1, max_length=120)
    category: str | None = Field(None, max_length=60)
    unit: Unit | None = None
    reorder_level: float | None = Field(None, ge=0)
    selling_price: float | None = Field(None, gt=0)
    reference_commodity: str | None = None


class ProductOut(CamelModel):
    id: int
    name: str
    category: str | None = None
    unit: str
    current_stock: float
    reorder_level: float
    selling_price: float | None = None
    reference_commodity: str | None = None
    stock_status: str                                          # In Stock / Low Stock / Out of Stock


# =====================================================================
# Suppliers
# =====================================================================
class SupplierIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    contact: str | None = Field(None, max_length=60)
    address: str | None = Field(None, max_length=250)
    product_ids: list[int] = []


class SupplierOut(CamelModel):
    id: int
    name: str
    contact: str | None = None
    address: str | None = None
    product_ids: list[int] = []
    product_names: list[str] = []


# =====================================================================
# Purchases and sales
# =====================================================================
class PurchaseCreate(CamelModel):
    product_id: int
    supplier_id: int
    quantity: float = Field(gt=0, le=1_000_000)
    unit_price: float = Field(gt=0, le=10_000_000)             # Rs PER UNIT
    purchase_date: dt.date


class PurchaseOut(CamelModel):
    id: int
    product_id: int
    product_name: str
    unit: str | None = None
    supplier_id: int | None = None
    supplier_name: str | None = None
    quantity: float
    unit_price: float
    total: float
    purchase_date: dt.date
    insights: dict | None = None                               # filled by the anomaly check after POST


class PurchasePage(CamelModel):
    items: list[PurchaseOut]
    total: int
    page: int
    page_size: int


class SaleCreate(CamelModel):
    product_id: int
    quantity: float = Field(gt=0, le=1_000_000)
    unit_price: float | None = Field(None, gt=0, le=10_000_000)   # default: the product's selling price
    sale_date: dt.date


class SaleOut(CamelModel):
    id: int
    product_id: int
    product_name: str
    unit: str | None = None
    quantity: float
    unit_price: float
    total: float
    sale_date: dt.date


class SalePage(CamelModel):
    items: list[SaleOut]
    total: int
    page: int
    page_size: int


class ActivityOut(CamelModel):
    id: int
    kind: str | None = None
    text: str | None = None
    created_at: dt.datetime | None = None


class PasswordChange(BaseModel):
    oldPassword: str = Field(..., min_length=1)
    newPassword: str = Field(..., min_length=6, max_length=128)
