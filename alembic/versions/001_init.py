"""initial schema

Revision ID: 001_init
Revises:
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = "001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v_type",
        sa.Column("id_v_type", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
    )

    op.create_table(
        "brand",
        sa.Column("id_brand", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("country", sa.String(60)),
    )

    op.create_table(
        "m_type",
        sa.Column("id_m_type", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("params", sa.Text, default=""),
    )

    op.create_table(
        "shop",
        sa.Column("id_shop", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("city", sa.String(80)),
    )

    op.create_table(
        "shop_website",
        sa.Column("id_site", sa.Integer, primary_key=True),
        sa.Column("id_shop", sa.Integer,
                  sa.ForeignKey("shop.id_shop", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(255), nullable=False),
        sa.Column("parser_code", sa.String(40), nullable=False),
    )

    op.create_table(
        "product",
        sa.Column("id_product", sa.Integer, primary_key=True),
        sa.Column("id_v_type", sa.Integer, sa.ForeignKey("v_type.id_v_type")),
        sa.Column("id_brand",  sa.Integer, sa.ForeignKey("brand.id_brand")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sku",  sa.String(64), nullable=False, unique=True),
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("cost", sa.Numeric(12, 2)),
        sa.Column("search_query", sa.String(200)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "product_parameter",
        sa.Column("id_param", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("unit", sa.String(20)),
    )

    op.create_table(
        "parameter_value",
        sa.Column("id_value", sa.Integer, primary_key=True),
        sa.Column("id_param",   sa.Integer, sa.ForeignKey("product_parameter.id_param")),
        sa.Column("id_product", sa.Integer, sa.ForeignKey("product.id_product", ondelete="CASCADE")),
        sa.Column("value", sa.String(120)),
    )

    op.create_table(
        "competitor_price",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("id_product", sa.Integer,
                  sa.ForeignKey("product.id_product", ondelete="CASCADE"), nullable=False),
        sa.Column("id_shop", sa.Integer, sa.ForeignKey("shop.id_shop"), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("url", sa.String(500)),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_cp_product_fetched", "competitor_price",
                    ["id_product", "fetched_at"])

    op.create_table(
        "app_user",
        sa.Column("id_user", sa.Integer, primary_key=True),
        sa.Column("login", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(120), nullable=False),
        sa.Column("role", sa.String(40), nullable=False, server_default="manager"),
        sa.Column("full_name", sa.String(160)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "product_shop",
        sa.Column("id_ps", sa.Integer, primary_key=True),
        sa.Column("id_product", sa.Integer,
                  sa.ForeignKey("product.id_product", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("id_m_type", sa.Integer, sa.ForeignKey("m_type.id_m_type")),
        sa.Column("price_min", sa.Numeric(12, 2)),
        sa.Column("price_max", sa.Numeric(12, 2)),
        sa.Column("approved_price", sa.Numeric(12, 2)),
        sa.Column("approved_at", sa.DateTime),
        sa.Column("approved_by", sa.Integer, sa.ForeignKey("app_user.id_user")),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ts", sa.DateTime, server_default=sa.func.now()),
        sa.Column("id_user", sa.Integer, sa.ForeignKey("app_user.id_user")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_id", sa.Integer),
        sa.Column("payload", sa.Text),
    )


def downgrade() -> None:
    for t in ["audit_log", "product_shop", "app_user", "competitor_price",
              "parameter_value", "product_parameter", "product",
              "shop_website", "shop", "m_type", "brand", "v_type"]:
        op.drop_table(t)
