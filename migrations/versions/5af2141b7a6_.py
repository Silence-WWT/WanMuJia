"""empty message

Revision ID: 5af2141b7a6
Revises: 3f46fe4e131
Create Date: 2015-07-22 15:41:51.236402

"""

# revision identifiers, used by Alembic.
revision = '5af2141b7a6'
down_revision = '3f46fe4e131'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('distributors', sa.Column('is_revoked', sa.Boolean(), nullable=False))
    op.drop_column('distributors', 'deleted_confirmed')
    op.drop_column('distributors', 'is_deleted')
    op.drop_index('mobile', table_name='privileges')
    op.drop_column('privileges', 'mobile')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('privileges', sa.Column('mobile', mysql.CHAR(length=11), nullable=False))
    op.create_index('mobile', 'privileges', ['mobile'], unique=True)
    op.add_column('distributors', sa.Column('is_deleted', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False))
    op.add_column('distributors', sa.Column('deleted_confirmed', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False))
    op.drop_column('distributors', 'is_revoked')
    ### end Alembic commands ###