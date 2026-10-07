"""tenant slug branding and role module permissions

Revision ID: 89a7fc13e3ec
Revises: e98046061ba0
Create Date: 2026-08-29 15:46:41.101091

"""
import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '89a7fc13e3ec'
down_revision = 'e98046061ba0'
branch_labels = None
depends_on = None

DEFAULT_ROLE_MODULES = {
    "bookkeeper": ["dashboard", "invoices", "exceptions"],
    "accountant_manager": ["dashboard", "invoices", "exceptions", "approvals", "erp_connectors"],
    "admin": ["dashboard", "invoices", "exceptions", "approvals", "audit_log", "erp_connectors", "users", "branding"],
    "auditor": ["dashboard", "audit_log"],
}


def upgrade() -> None:
    op.create_table(
        'role_module_permissions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('module', sa.String(length=32), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'role', 'module', name='uq_role_module_tenant'),
    )
    op.create_index(op.f('ix_role_module_permissions_tenant_id'), 'role_module_permissions', ['tenant_id'], unique=False)

    # Nullable first — existing rows get backfilled below, then we tighten.
    op.add_column('tenants', sa.Column('slug', sa.String(length=64), nullable=True))
    op.add_column('tenants', sa.Column('primary_color', sa.String(length=16), nullable=True))
    op.add_column('tenants', sa.Column('logo_object_key', sa.String(), nullable=True))

    bind = op.get_bind()
    existing_tenants = bind.execute(sa.text("SELECT id, name FROM tenants")).fetchall()

    now = sa.func.now()
    for tenant_id, name in existing_tenants:
        slug = sa.text(
            "trim(both '-' from regexp_replace(lower(:name), '[^a-z0-9]+', '-', 'g'))"
        )
        bind.execute(
            sa.text(
                "UPDATE tenants SET slug = " + slug.text + ", primary_color = '#059669' WHERE id = :id"
            ),
            {"name": name, "id": tenant_id},
        )

        for role, modules in DEFAULT_ROLE_MODULES.items():
            for module in modules:
                bind.execute(
                    sa.text(
                        "INSERT INTO role_module_permissions "
                        "(id, tenant_id, role, module, created_at, updated_at) "
                        "VALUES (:id, :tenant_id, :role, :module, now(), now())"
                    ),
                    {"id": str(uuid.uuid4()), "tenant_id": tenant_id, "role": role, "module": module},
                )

    op.alter_column('tenants', 'slug', nullable=False)
    op.alter_column('tenants', 'primary_color', nullable=False)
    op.create_index(op.f('ix_tenants_slug'), 'tenants', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_tenants_slug'), table_name='tenants')
    op.drop_column('tenants', 'logo_object_key')
    op.drop_column('tenants', 'primary_color')
    op.drop_column('tenants', 'slug')
    op.drop_index(op.f('ix_role_module_permissions_tenant_id'), table_name='role_module_permissions')
    op.drop_table('role_module_permissions')
