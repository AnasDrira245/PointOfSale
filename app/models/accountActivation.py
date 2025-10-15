from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, func
from ..database import Base
from app.enums import TokenStatus

class AccountActivation(Base):
    __tablename__ = "account_activation"
    
    id = Column(Integer, primary_key = True)
    employee_id= Column(Integer, ForeignKey("employees.id"), nullable = False)
    email = Column(String, nullable = False)
    token = Column(String, nullable = False)
    status = Column(Enum(TokenStatus), nullable = False)
    created_on = Column(DateTime, nullable = False, server_default=func.now())
