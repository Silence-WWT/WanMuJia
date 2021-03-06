"""empty message

Revision ID: 5abd389515d
Revises: adf62ad80
Create Date: 2015-11-18 17:41:45.993924

"""

# revision identifiers, used by Alembic.
revision = '5abd389515d'
down_revision = 'adf62ad80'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('username', sa.Unicode(length=30), nullable=False))
    op.add_column('users', sa.Column('username_revisable', sa.Boolean(), nullable=False))
    op.drop_column('users', 'nickname')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('nickname', mysql.VARCHAR(length=30), nullable=False))
    op.drop_column('users', 'username_revisable')
    op.drop_column('users', 'username')
    ### end Alembic commands ###
