from sqlalchemy import Column, String,Integer
from ..database import Base

class JwtBlackList(Base):
    __tablename__="jwt_blacklist"

    id = Column(Integer,primary_key=True,nullable=False)
    token = Column(String , nullable=False)
    