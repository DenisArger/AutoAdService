from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("password_hash", sa.String, nullable=False),
        sa.Column("role", sa.String, nullable=False, server_default="admin"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "cars",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand", sa.String, nullable=False),
        sa.Column("model", sa.String, nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("price", sa.Integer, nullable=False),
        sa.Column("color", sa.String, nullable=False),
        sa.Column("url", sa.String, nullable=False, unique=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("cars_brand_idx", "cars", ["brand"])
    op.create_index("cars_model_idx", "cars", ["model"])
    op.create_index("cars_year_idx", "cars", ["year"])
    op.create_index("cars_price_idx", "cars", ["price"])
    op.create_index("cars_color_idx", "cars", ["color"])

def downgrade():
    op.drop_index("cars_color_idx", table_name="cars")
    op.drop_index("cars_price_idx", table_name="cars")
    op.drop_index("cars_year_idx", table_name="cars")
    op.drop_index("cars_model_idx", table_name="cars")
    op.drop_index("cars_brand_idx", table_name="cars")
    op.drop_table("cars")
    op.drop_table("users")
