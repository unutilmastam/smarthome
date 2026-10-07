import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_migrations", ROOT / "scripts" / "check_migrations.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

HEAD = "from alembic import op\nimport sqlalchemy as sa\nrevision='x'\ndown_revision=None\n"


def run(tmp_path, body, contract=False):
    f = tmp_path / "m.py"
    f.write_text(HEAD + ("CONTRACT = True\n" if contract else "") + "def upgrade():\n" + body +
                 "\ndef downgrade():\n    pass\n")
    return cm.check_file(f)


def test_real_migrations_are_expand_only():
    assert cm.main([str(ROOT / "migrations" / "versions")]) == 0


def test_expand_is_fine(tmp_path):
    assert run(tmp_path, "    op.create_table('t', sa.Column('id', sa.Integer))\n"
                         "    op.add_column('t', sa.Column('x', sa.String(), nullable=True))\n"
                         "    op.add_column('t', sa.Column('y', sa.String(), nullable=False, server_default='a'))\n") == []


def test_destructive_needs_contract(tmp_path):
    for body in ("    op.drop_column('t', 'x')\n", "    op.drop_table('t')\n",
                 "    op.alter_column('t', 'x', new_column_name='y')\n",
                 "    op.alter_column('t', 'x', nullable=False)\n",
                 "    op.execute('DROP TABLE t')\n",
                 "    with op.batch_alter_table('t') as b:\n        b.drop_column('x')\n"):
        assert run(tmp_path, body), body


def test_not_null_without_default(tmp_path):
    assert run(tmp_path, "    op.add_column('t', sa.Column('x', sa.String(), nullable=False))\n")


def test_contract_rules(tmp_path):
    assert run(tmp_path, "    op.drop_column('t', 'x')\n", contract=True) == []
    assert run(tmp_path, "    op.drop_column('t', 'x')\n    op.add_column('t', sa.Column('y', sa.Integer(), nullable=True))\n", contract=True)
    assert run(tmp_path, "    op.add_column('t', sa.Column('y', sa.Integer(), nullable=True))\n", contract=True)
