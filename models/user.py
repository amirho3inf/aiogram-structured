from sqlalchemy import String, Column, Boolean, DateTime, BigInteger, Integer
from datetime import datetime as dt

from bot import db


class User(db.Model):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(128))
    age = Column(Integer, nullable=False)
    phone_number = Column(BigInteger, nullable=False)
    username = Column(String(32), nullable=True)
    joined_at = Column(DateTime, nullable=False, default=dt.utcnow)
    blocked = Column(Boolean, nullable=False, default=False)
    deactived = Column(Boolean, nullable=False, default=False)
