from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    last_name = Column(String(100))
    email = Column(String(150), unique=True, index=True, nullable=False)
    company = Column(String(150))
    password = Column(String(255), nullable=False)
    plan = Column(String(50), default="Starter")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(150), nullable=False)
    plan = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String(50), default="completed")
    stripe_id = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    company = Column(String(150))
    service = Column(String(100))
    message = Column(String(1000))
    created_at = Column(DateTime, server_default=func.now())
