from sqlalchemy import Column, Integer, String, func, DateTime
from ..database import Base


class Error(Base):
    __tablename__ = "errors"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    created_on = Column(DateTime, nullable=False, server_default=func.now())
