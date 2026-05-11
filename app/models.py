"""ORM-модели согласно даталогической модели из ВКР (раздел 2.3)."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String, Integer, Numeric, DateTime, ForeignKey, Boolean, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class VType(Base):
    """Вид товара (шины, диски и т. п.)."""
    __tablename__ = "v_type"
    id_v_type: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class Brand(Base):
    __tablename__ = "brand"
    id_brand: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    country: Mapped[str | None] = mapped_column(String(60), nullable=True)


class MType(Base):
    """Модель ценообразования."""
    __tablename__ = "m_type"
    id_m_type: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)  # cost|market|combined
    name: Mapped[str] = mapped_column(String(120))
    # коэффициенты в JSON-подобной структуре (текст с парами key=value)
    params: Mapped[str] = mapped_column(Text, default="")


class Shop(Base):
    """Магазин-конкурент."""
    __tablename__ = "shop"
    id_shop: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)


class ShopWebsite(Base):
    __tablename__ = "shop_website"
    id_site: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_shop: Mapped[int] = mapped_column(ForeignKey("shop.id_shop", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(255))
    parser_code: Mapped[str] = mapped_column(String(40))  # wildberries|ozon|demo


class Product(Base):
    __tablename__ = "product"
    id_product: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_v_type: Mapped[int | None] = mapped_column(ForeignKey("v_type.id_v_type"))
    id_brand: Mapped[int | None] = mapped_column(ForeignKey("brand.id_brand"))
    name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    search_query: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                  onupdate=datetime.utcnow)
    v_type = relationship("VType")
    brand = relationship("Brand")


class ProductParameter(Base):
    __tablename__ = "product_parameter"
    id_param: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)


class ParameterValue(Base):
    __tablename__ = "parameter_value"
    id_value: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_param: Mapped[int] = mapped_column(ForeignKey("product_parameter.id_param"))
    id_product: Mapped[int] = mapped_column(ForeignKey("product.id_product", ondelete="CASCADE"))
    value: Mapped[str] = mapped_column(String(120))


class CompetitorPrice(Base):
    """Снимок цены конкурента."""
    __tablename__ = "competitor_price"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_product: Mapped[int] = mapped_column(ForeignKey("product.id_product", ondelete="CASCADE"))
    id_shop: Mapped[int] = mapped_column(ForeignKey("shop.id_shop"))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("ix_cp_product_fetched", "id_product", "fetched_at"),
    )


class ProductShop(Base):
    """Утверждённая цена / вилка для товара."""
    __tablename__ = "product_shop"
    id_ps: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_product: Mapped[int] = mapped_column(ForeignKey("product.id_product", ondelete="CASCADE"),
                                            unique=True)
    id_m_type: Mapped[int | None] = mapped_column(ForeignKey("m_type.id_m_type"))
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    approved_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id_user"), nullable=True)


class AppUser(Base):
    __tablename__ = "app_user"
    id_user: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(40), default="manager")  # admin|manager|sales|audit
    full_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    id_user: Mapped[int | None] = mapped_column(ForeignKey("app_user.id_user"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
