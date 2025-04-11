from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.emailUtils import simple_send
from app.enums import tokenStatus
from app.enums.accountStatus import AccountStatus

from . import models,schemas
import uuid

def get_account_by_token(db:Session, token:str):
    return db.query(models.AccountActivation).filter(models.AccountActivation.token==token).first()

def get_user(db:Session, id:int):
    return db.query(models.Employee).filter(models.Employee.id==id).first()

def get_by_email(db:Session, email:str):
    return db.query(models.Employee).filter(models.Employee.email==email).first()

def get_users(db:Session, skip:int=0, limit:int=100):
    return db.query(models.Employee).offset(skip).limit(limit).all()

async def add(db:Session, employee:schemas.EmployeeCreate):

    try:

        employee.password = employee.password + "notreallyhashed"

        employee_data = employee.model_dump()
        employee_data.pop('confirm_password')
        roles = employee_data.pop("roles")

        #add employee
        #fl moment hedha db_model 3ndeha id = null
        db_employee=models.Employee(**employee_data)
        db.add(db_employee)
        db.flush() #tsajel el change fel db and then we will see commit vs flush 


        # #add employee_roles
        # for role in roles:
        #     db_role=models.EmployeeRole(role=role,employee_id=db_employee.id)
        #     db.add(db_role)
        #     db.flush() #tsajel el change fel db and then we will see commit vs flush 
        #     db.refresh(db_role) # b3d refresh , db 3tat id ll role and we will get the id 
        
        db_role = [models.EmployeeRole(role=role,employee_id=db_employee.id) for role in roles]
        db.add_all(db_role)
       
    
        # add confirmation code 
        confirmation_code = str(uuid.uuid1())
        accountActivation = models.AccountActivation(employee_id=db_employee.id,email=db_employee.email,token=confirmation_code,status="Pending")
        db.add(accountActivation)
      

        #send confirmation email
        # lezm email service   
        await  simple_send(schemas.EmailSchema(email=[db_employee.email],body={
            'code':confirmation_code
        }         ))

        db.commit()

    except Exception as e:
        print(e)
        db.rollback()

    return schemas.EmployeeOut(**db_employee.__dict__)


