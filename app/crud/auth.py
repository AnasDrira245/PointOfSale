from sqlalchemy.orm import Session
import uuid
from app import models, enums


# confirm account code
def get_confirmation_code(db: Session, code: str):
    return db.query(models.AccountActivation).filter(models.AccountActivation.token == code).first()

def add_confirmation_code(db: Session, id: int, email: str):
    activation_code = models.AccountActivation(employee_id=id, email=email, status=enums.TokenStatus.Pending, token=uuid.uuid1())
    db.add(activation_code)

    return activation_code

def edit_confirmation_code(db: Session, id: int, new_data: dict):
    db.query(models.AccountActivation).filter(models.AccountActivation.id == id).update(new_data, synchronize_session=False)

# reset psw code
def get_reset_code(db: Session, code: str):
    return db.query(models.ResetPassword).filter(models.ResetPassword.token == code).first()

def add_reset_code(db: Session, db_employee: models.Employee):
    reset_code = models.ResetPassword(employee_id=db_employee.id, email=db_employee.email, status=enums.TokenStatus.Pending, token=uuid.uuid1())
    db.add(reset_code)

    return reset_code

def edit_reset_code(db: Session, id: int, new_data: dict):
    db.query(models.ResetPassword).filter(models.ResetPassword.id == id).update(new_data, synchronize_session=False)
