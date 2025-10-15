from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.OAuth2 import get_password_hash

from app import models, schemas, enums
from app.crud.auth import add_confirmation_code
from app.dependencies import PagiantionParams
from app.external_services import emailService

error_keys = {
    "employee_roles_employee_id_fkey": "No Employee with this id",
    "employee_roles_pkey": "No Employee Role with this id",
    "ck_employees_cnss_number": "It should be {8 digits}-{2 digits} and it's Mandatory for Cdi and Cdd",
    "employees_email_key": "Email already used",
    "employees_pkey": "No employee with this id",
}

# Employee crud
def get_employee(db: Session, id: int):
    return db.query(models.Employee).filter(models.Employee.id == id).first()

# to refactor later
def get_employee_by_email(db: Session, email: str):
    return db.query(models.Employee).filter(models.Employee.email == email).first()

def sudo_edit_employee(db: Session, id: int, new_data: dict):
    db.query(models.Employee).filter(models.Employee.id == id).update(new_data, synchronize_session=False)

# to move to common place
def div_ceil(nominator, denominator):
    full_pages = nominator // denominator
    additional_page = 1 if nominator % denominator > 0 else 0
    return full_pages + additional_page

def get_employees(db: Session, pagination_param: PagiantionParams, name_substr: str):
    query = db.query(models.Employee)

    if name_substr:
        query = query.filter(func.lower(func.concat(models.Employee.first_name, ' ', models.Employee.last_name)).contains(func.lower(name_substr)))
    
    total_records = query.count()
    total_pages = div_ceil(total_records, pagination_param.page_size)
    employees = query.limit(pagination_param.page_size).offset((pagination_param.page_number-1)*pagination_param.page_size).all()
    return (employees, total_records, total_pages)

async def add_employee(db: Session, employee: schemas.EmployeeCreate):
    employee.password = get_password_hash(employee.password)
    employee_data = employee.model_dump()
    employee_data.pop('confirm_password')
    roles = employee_data.pop('roles')
    # add employee
    db_employee = models.Employee(**employee_data)
    db.add(db_employee) 
    db.flush()
    # add employee roles
    db.add_all([models.EmployeeRole(role=role, employee_id=db_employee.id) for role in roles])
    #add confirmation code 
    activation_code = add_confirmation_code(db, db_employee.id, db_employee.email)
    
    # send confirmation email
    await emailService.simple_send([db_employee.email], {
            'name': db_employee.first_name,
            'code': activation_code.token,
            'psw': employee.password,
        }, enums.EmailTemplate.ConfirmAccount,
    )
    db.commit()
    return db_employee

async def edit_employee(db: Session, id: int, entry: schemas.EmployeeEdit):
    query = db.query(models.Employee).filter(models.Employee.id == id)
    employee_in_db = query.first()

    if not employee_in_db:
        raise HTTPException(status_code=400, detail="Employee not found")
    
    fields_to_update = entry.model_dump()
    for field in ["email", "password", "confirm_password", "roles", "actual_password"]:
        fields_to_update.pop(field)
    
    # manage roles after reading about relationships (manage access role)

    # if edited email
    if employee_in_db.email != entry.email:
        if not entry.actual_password or get_password_hash(entry.password) != employee_in_db.password:
            raise HTTPException(status_code=400, detail="Current Password missing or incorrect. It's mandatory to set a new email")
        
        fields_to_update[models.Employee.email] = entry.email
        fields_to_update[models.Employee.account_status] = enums.AccountStatus.Inactive

    # if edited psw
    if entry.password and get_password_hash(entry.password) != employee_in_db.password:
        if entry.password != entry.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords must match")
        
        if not entry.actual_password or get_password_hash(entry.actual_password) != employee_in_db.password:
            raise HTTPException(status_code=400, detail="Current Password missing or incorrect. It's mandatory to set a new password")
        
        fields_to_update[models.Employee.password] = get_password_hash(entry.password)

    query.update(fields_to_update, synchronize_session=False)

    if models.Employee.email in fields_to_update:
        activation_code = add_confirmation_code(db, employee_in_db.id, fields_to_update[models.Employee.email])
    
        # send confirmation email
        await emailService.simple_send([employee_in_db.email], {
                'name': employee_in_db.first_name,
                'code': activation_code.token,
            }, enums.EmailTemplate.ConfirmAccount,
        )
    
    db.commit()



