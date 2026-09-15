from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """
    Users table (Member 1 - User & Shop Management module, per VyapariAI work plan).
    This is the first table needed since Login/Signup only depend on Users.
    Shops and Products tables will be added next, once Shop Setup is wired up.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
