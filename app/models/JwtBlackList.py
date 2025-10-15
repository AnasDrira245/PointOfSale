from sqlalchemy import Column, Integer, String
from ..database import Base

class JwtBlacklist(Base):
    __tablename__ = "jwt_blacklist"

    id = Column(Integer, primary_key = True, nullable = False)
    token = Column(String, nullable = False)
