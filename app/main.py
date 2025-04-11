from datetime import datetime
from typing import List
from fastapi import Depends, FastAPI, HTTPException,status
from sqlalchemy.orm import Session

from app import crud, enums, schemas,models

from app import emailUtils

from app.database import SessionLocal

import re
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {
        "message": "Hello World"
    }

@app.post("/employee/",response_model=schemas.EmployeeOut)
async def create_employee(employee:schemas.EmployeeCreate, db:Session=Depends(get_db)):

    if(employee.password != employee.confirm_password):
        raise HTTPException(status_code=400,detail="Passwords do not match")
    db_employee = crud.get_by_email(db,email = employee.email)
    if db_employee:
        raise HTTPException(status_code=400,detail="Email already registered")
    
    return await  crud.add(db = db , employee  = employee)


@app.patch("/employee",response_model=schemas.BaseOut)
def confirm_account(confirmAccount:schemas.ConfimAccount,db:Session=Depends(get_db)):

    account = crud.get_account_by_token(db,confirmAccount.confirmation_code)
    if not account:
        raise HTTPException(status_code=404,detail="Token not found")
    if account.status == enums.TokenStatus.Used:
        raise HTTPException(status_code=400,detail="Token already Used")
    
    #expired or not?
    diff = (datetime.now() - account.created_on).seconds

    if (diff>3600):
        raise HTTPException(status_code=400,detail="Token expired")
    
    db.query(models.Employee).filter(models.Employee.id==account.employee_id).\
    update({models.Employee.account_status:enums.AccountStatus.Active},synchronize_session=False)

    db.commit()

    db.query(models.AccountActivation).filter(models.AccountActivation.id==account.id).\
    update({models.AccountActivation.status:enums.TokenStatus.Used},synchronize_session=False)

    db.commit()

    return schemas.BaseOut(
        detail="Account confirmed",
        status_code=status.HTTP_200_OK
        )

email_regex  =  r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
cnss_number_regex= r"^\d{8}-\d{2}$"
phone_number_regex = r"^\+216\d{8}$"

mandatory_fields={
    "first_name":"First Name",
    "last_name":"Last Name",
    "email":"Email",
    "password":"Password",
    "number":"Number",
    "contract_type":"Contract Type",
    "gender":"Gender",
    "employee_roles":"Roles",
}

optional_fields={
    "birth_date":"Birth Date",
    "address":"Address",
    "phone_number":"Phone Number",
}

mandatory_with_condition={
    "cnss_number":("Cnss Number", lambda employee :isCdiOrCdd(employee) ) 

}
possible_fields={
    **mandatory_fields,
    **optional_fields,
    **mandatory_with_condition
}


options = [
    schemas.MatchyOption(display_value=mandatory_fields["first_name"],value="first_name",mandatory=True,type=enums.FieldType.string),
    schemas.MatchyOption(display_value=mandatory_fields["last_name"],value="last_name",mandatory=True,type=enums.FieldType.string), 
    schemas.MatchyOption(display_value=mandatory_fields["email"],value="email",mandatory=True,type=enums.FieldType.string,conditions=[
        schemas.MatchyCondition(proprety=enums.ConditionProperty.regex,comparer=enums.Comparer.e,value=email_regex)
    ]),
    schemas.MatchyOption(display_value=mandatory_fields["password"],value="password",mandatory=True,type=enums.FieldType.string),
    schemas.MatchyOption(display_value=mandatory_fields["number"],value="number",mandatory=True,type=enums.FieldType.integer),
    schemas.MatchyOption(display_value=optional_fields["birth_date"],value="birth_date",mandatory=False,type=enums.FieldType.string),
    schemas.MatchyOption(display_value=optional_fields["address"],value="address",mandatory=False,type=enums.FieldType.string),
    schemas.MatchyOption(display_value=mandatory_with_condition["cnss_number"][0],value="cnss_number",mandatory=False,type=enums.FieldType.string),
    schemas.MatchyOption(display_value=mandatory_fields["contract_type"],value="contract_type",mandatory=True,type=enums.FieldType.string,conditions=[
        schemas.MatchyCondition(proprety=enums.ConditionProperty.value,comparer=enums.Comparer.in_,value=enums.ContractType.getPossibleValues())
    ]),
     schemas.MatchyOption(display_value=mandatory_fields["gender"],value="gender",mandatory=True,type=enums.FieldType.string,conditions=[
        schemas.MatchyCondition(proprety=enums.ConditionProperty.value,comparer=enums.Comparer.in_,value=enums.Gender   .getPossibleValues())
    ]),
     schemas.MatchyOption(display_value=mandatory_fields["employee_roles"],value="employee_roles",mandatory=True,type=enums.FieldType.string),
    schemas.MatchyOption(display_value=optional_fields["phone_number"],value="phone_number",mandatory=False,type=enums.FieldType.string,conditions=[
        schemas.MatchyCondition(proprety=enums.ConditionProperty.regex,comparer=enums.Comparer.e,value=phone_number_regex) ])
 
 ] 



            
def is_regex_matched(pattern,field):
    return field if re.match(pattern,field) else None #idha warning n5aliwha none , idha error (mandatory )-->error

#fix me later move to utils file
def is_valid_email(email:str):
    return email if is_regex_matched(email_regex,email)else None 

def is_positive_int(field:str):
    try:
        field = int(field)
    except Exception as e:
        return None
    
    return field if  field >= 0 else None

def is_valid_date(field):
    #FIX ME LATER : try to give the user the possibility to choose the date format
    try:
        obj = datetime.strptime(field,'%d/%m/%Y')
        return  obj.isoformat()
    except Exception as e:
        return None # fchel eno yrodeha date --> not parsable to int 

def isCdiOrCdd(employee):
    return employee["contract_type"].value in [enums.ContractType.Cdi,enums.ContractType.Cdd]
def is_valid_cnss_number(field):
    return field if is_regex_matched(cnss_number_regex,field) else None
    

def is_valid_phone_number(field):
    return field if is_regex_matched(phone_number_regex,field) else None

def are_roles_valid(field):
    roles_names = field.split(',')
    res=[]
    for role_name in roles_names:
        val =  enums.RoleType.is_valid_enum_value(role_name)
        if not val:
            return None
        else:
            res.append(val)
    return res
   
    

fields_check={

    "email": ( lambda field : is_valid_email(field)   , "Wrong email format" ),
    "gender": (lambda field : enums.Gender.is_valid_enum_value(field), f"Possible values are {enums.Gender.getPossibleValues()}"),
    "contract_type": (lambda field : enums.ContractType.is_valid_enum_value(field), f"Possible values are {enums.ContractType.getPossibleValues()}"), 
    "number":(lambda field : is_positive_int(field) , "It should be an integer >=0 "),
    "birth_date": (lambda field : is_valid_date(field), "Wrong date format it should be dd/mm/yyyy"),
    "cnss_number":(lambda field : is_valid_cnss_number(field), "It Should be {8 digits}-{2 digits} and it's Mandatory only for cdd and cdi  "),
    "phone_number":(lambda field : is_valid_phone_number(field), "It should be +216 followed by 8 digits"),
    "employee_roles":(lambda field : are_roles_valid(field), f"Possible values are {enums.RoleType.getPossibleValues()}"),
}
    
def is_field_mondatory(employee,field):
    return field in mandatory_fields or (field in mandatory_with_condition[field][1](employee) )

#employee wehed 
def validate_employee_data(employee):
    errors=[]
    warnings=[]
    wrong_cells=[] #bch nraj3ouhom lel matchy ylawenhom bel a7mar
    employee_to_add= {field:cell.value for field ,cell in employee.items()}
    for field in possible_fields:
        if field not in employee:
            if is_field_mondatory(employee,field):
                errors.append(f"{possible_fields[field]} is mondatory but missing") 
            continue
        cell = employee[field]
        employee_to_add[field]=employee_to_add[field].strip()
        if employee_to_add[field] == "":
            if is_field_mondatory(employee,field):
                msg=f"{possible_fields[field]} is mondatory but empty";
                errors.append(msg) 
                wrong_cells.append(schemas.MatchyWrongCell(msg,cell.rowIndex,cell.colIndex))
            else: 
                employee_to_add[field]=None # f db ttsab null
        elif field in fields_check:
            converted_val= fields_check[field][0](employee_to_add[field]) 
            if converted_val is None:
                msg=fields_check[field][1]
                (errors if is_field_mondatory(employee,field) else warnings).append(msg)
                wrong_cells.append(schemas.MatchyWrongCell(msg,cell.rowIndex,cell.colIndex))
            else:
                employee_to_add[field]=converted_val   
    
    return (errors,warnings,wrong_cells,employee_to_add)
          

def validate_employees_data_and_upload(employees:list,force_upload:bool,db:Session=Depends(get_db)):
    errors=[]
    warnings=[]
    wrong_cells=[]
    employee_to_add=[] #bech nst3mlouha fel batch add mb3d , bech nlemo data kol w nsobo fard mara

    for line,employee in enumerate(employees):
        emp_errors,emp_warnings,emp_wrong_cells,emp=validate_employee_data(employee)
        if emp_errors:
            msg = ('\n').join(emp_errors)
            errors.append(f"\nLine{line+1} : \n {msg}") 
        if emp_warnings:
            msg = ('\n').join(emp_warnings)
            warnings.append(f"\nLine{line+1} : \n {msg}") 
        if emp_wrong_cells:
            wrong_cells.extend(emp_wrong_cells)
        employee_to_add.append(emp)
    
    if errors or (warnings and  not force_upload): 
        return schemas.ImportResponse(
            errors= ('\n').join(errors),
            warnings=('\n').join(warnings),
            wrong_cells=wrong_cells
        )

    



@app.post("/employee/import")
def import_employees():
    pass


@app.get("/employees/possibleImportFields")
def getPossibleFields(db:Session=Depends(get_db)):
    return schemas.ImportPossibleFields(
        possibleFields=options,
    )


@app.post("employees/csv")
def upload(entry:schemas.MatchyUploadEntry,db:Session=Depends(get_db)):
    employees = entry.lines
    if not employees: # front lezmou ygeri fama au moins ligne
        raise HTTPException(status_code=400,detail="Nothing to do , empty file")
    
    
    missing_mandatory_fields= set(mandatory_fields.keys()) - set(employees[0].keys)   

    if missing_mandatory_fields:
        fields_names=[display for field,display in mandatory_fields.items()]
        raise HTTPException(status_code=400,
                            detail=f"Missing mandatory fields {(', ').join(fields_names)}")

