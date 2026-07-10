"""seed default data

Revision ID: 732afc82d6d1
Revises: a07d4b037809
Create Date: 2026-07-10 01:11:04.979117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '732afc82d6d1'
down_revision: Union[str, Sequence[str], None] = 'a07d4b037809'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


suspicious_patterns_table = sa.table(
    "suspicious_patterns",
    sa.column("pattern", sa.Text),
    sa.column("is_regex", sa.Boolean),
    sa.column("description", sa.String),
    sa.column("enabled", sa.Boolean),
    sa.column("severity", sa.String),
)

global_config_table = sa.table(
    "global_config",
    sa.column("id", sa.Integer),
    sa.column("digest_hour", sa.Integer),
    sa.column("digest_timezone", sa.String),
    sa.column("ssl_alert_days_json", sa.JSON),
    sa.column("domain_alert_days_json", sa.JSON),
    sa.column("panel_base_url", sa.String),
)

DEFAULT_PATTERNS = [
    {
        "pattern": "eval(atob(",
        "is_regex": False,
        "description": "Obfuscated eval of base64-decoded JS (common malware loader)",
        "enabled": True,
        "severity": "critical",
    },
    {
        "pattern": "String.fromCharCode",
        "is_regex": False,
        "description": "Char-code obfuscated inline script",
        "enabled": True,
        "severity": "critical",
    },
    {
        "pattern": r"(?i)(verify you are human|click here to verify|copy and paste this).{0,200}(win\+r|ctrl\+v|powershell)",
        "is_regex": True,
        "description": "ClickFix-style fake verification prompt instructing the user to run a command",
        "enabled": True,
        "severity": "critical",
    },
    {
        "pattern": r"(?i)cloudflare.{0,80}(verification|captcha).{0,200}(win\+r|powershell|cmd\.exe)",
        "is_regex": True,
        "description": "ClearFake-style fake Cloudflare verification widget",
        "enabled": True,
        "severity": "critical",
    },
]


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(suspicious_patterns_table, DEFAULT_PATTERNS)
    op.bulk_insert(
        global_config_table,
        [
            {
                "id": 1,
                "digest_hour": 9,
                "digest_timezone": "America/Argentina/Buenos_Aires",
                "ssl_alert_days_json": [14, 7, 3],
                "domain_alert_days_json": [30, 14, 7],
                "panel_base_url": "http://localhost:8000",
            }
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(global_config_table.delete().where(global_config_table.c.id == 1))
    op.execute(
        suspicious_patterns_table.delete().where(
            suspicious_patterns_table.c.pattern.in_([p["pattern"] for p in DEFAULT_PATTERNS])
        )
    )
