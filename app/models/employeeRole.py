from sqlalchemy import Column , Integer , ForeignKey,Enum
from ..database import Base
from app.enums import RoleType

class EmployeeRole(Base):
    __tablename__ = "employee_roles"

    id = Column(Integer,primary_key=True,nullable=False)
    employee_id = Column(Integer,ForeignKey("employees.id"),nullable=False)
    role = Column(Enum(RoleType),nullable=False)