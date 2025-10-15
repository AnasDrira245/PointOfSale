from typing import Annotated
from fastapi import APIRouter, Depends
import uuid
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session
from app import crud, models, schemas, enums
from datetime import datetime
import re
from app.crud.employee import add_employee, edit_employee, get_employees
from app.database import get_db
from app.dependencies import DbDep, paginationParams, currentEmployee, get_current_employee
from app.external_services import emailService

app = APIRouter(
    prefix="/employee",
    tags=["Employee"],
)

error_keys = {
    "employee_roles_employee_id_fkey": "No Employee with this id",
    "employee_roles_pkey": "No Employee Role with this id",
    "ck_employees_cnss_number": "It should be {8 digits}-{2 digits} and it's Mandatory for Cdi and Cdd",
    "employees_email_key": "Email already used",
    "employees_pkey": "No employee with this id",
}

@app.post("/")
async def add(employee: schemas.EmployeeCreate, db: Session = Depends(get_db), current_user = Depends(get_current_employee)):
    try:
        await add_employee(db=db, employee=employee)
    except Exception as e:
        db.rollback()   
        text = str(e)
        add_error(text, db)
        return schemas.BaseOut(status_code=500, detail=get_error_message(text, error_keys))

    return schemas.BaseOut(status_code=201, detail="Employee added and email sent for confirmation")


@app.put("/{id}", response_model=schemas.BaseOut)
async def edit(id: int, entry: schemas.EmployeeEdit, db: DbDep):
    try:
        await edit_employee(db, id, entry)
    except Exception as e:
        db.rollback()
        text = str(e)
        add_error(text, db)
        raise HTTPException(status_code=500, detail=get_error_message(text, error_keys))
    
    return schemas.BaseOut(
        status_code=201,
        detail="User updated",
    )

@app.get("/all", response_model=schemas.EmployeesOut)
def get(db: DbDep, pagination_param: paginationParams, name_substr: str = None, current_user = Depends(get_current_employee)):
    try:
        employees, total_records, total_pages = get_employees(db, pagination_param, name_substr)
    except Exception as e:
        db.rollback()
        text = str(e)
        add_error(text, db)
        raise HTTPException(status_code=500, detail=get_error_message(text, error_keys))
    
    return schemas.EmployeesOut(
        status_code=200,
        detail="All employees",
        list=[schemas.EmployeeOut(**employee.__dict__, roles=[employee_role.role for employee_role in employee.roles]) for employee in employees], # to update later
        page_number=pagination_param.page_number, 
        page_size=pagination_param.page_size,
        total_pages=total_pages,
        total_records = total_records,
    )

email_regex = r'^\S+@\S+\.\S+$'
cnss_regex = r'^\d{8}-\d{2}$'
phone_number_regex = r'^\d{8}$'

mandatory_fields = {
    "first_name": "First Name",
    "last_name": "Last Name",
    "email": "Email",
    "number": "Number",
    "contract_type": "Contract Type",
    "gender": "Gender",
    "employee_roles": "Roles",
}


optional_fields = {
    "birth_date": "Birth Date",
    "address": "Address",
    "phone_number": "Phone Number",
}

mandatory_with_condition = {
    "cnss_number": ("Cnss Number", lambda employee: isCdiOrCdd(employee))
}

possible_fields = {
    **mandatory_fields,
    **optional_fields,
    **mandatory_with_condition,
} 

unique_fields = {
    "email": models.Employee.email,
    "number": models.Employee.number,
}

options = [
    schemas.MatchyOption(display_value=mandatory_fields["first_name"], value="first_name", mandatory=True, type=enums.FieldType.string),
    schemas.MatchyOption(display_value=mandatory_fields["last_name"], value="last_name", mandatory=True, type=enums.FieldType.string),
    schemas.MatchyOption(display_value=mandatory_fields["email"], value="email", mandatory=True, type=enums.FieldType.string, conditions=[
        schemas.MatchyCondition(property=enums.ConditionProperty.regex, comparer=enums.Comparer.e, value=email_regex),
    ]),
    schemas.MatchyOption(display_value=mandatory_fields["number"], value="number", mandatory=True, type=enums.FieldType.integer),
    schemas.MatchyOption(display_value=optional_fields["birth_date"], value="birth_date", mandatory=False, type=enums.FieldType.string),
    schemas.MatchyOption(display_value=optional_fields["address"], value="address", mandatory=False, type=enums.FieldType.string),
    schemas.MatchyOption(display_value=mandatory_with_condition["cnss_number"][0], value="cnss_number", mandatory=False, type=enums.FieldType.string, conditions=[
        schemas.MatchyCondition(property=enums.ConditionProperty.regex, comparer=enums.Comparer.e, value=cnss_regex)
    ]),
    schemas.MatchyOption(display_value=mandatory_fields["contract_type"], value="contract_type", mandatory=True, type=enums.FieldType.string, conditions=[
        schemas.MatchyCondition(property=enums.ConditionProperty.value, comparer=enums.Comparer._in, value=enums.ContractType.getPossibleValues())
    ]),
    schemas.MatchyOption(display_value=mandatory_fields["gender"], value="gender", mandatory=True, type=enums.FieldType.string, conditions=[
        schemas.MatchyCondition(property=enums.ConditionProperty.value, comparer=enums.Comparer._in, value=enums.Gender.getPossibleValues())
    ]),
    schemas.MatchyOption(display_value=mandatory_fields["employee_roles"], value="employee_roles", mandatory=True, type=enums.FieldType.string),
    schemas.MatchyOption(display_value=optional_fields["phone_number"], value="phone_number", mandatory=False, type=enums.FieldType.string, conditions=[
        schemas.MatchyCondition(property=enums.ConditionProperty.regex, comparer=enums.Comparer.e, value=phone_number_regex),
    ]),
]

def is_regex_matched(pattern, field):
    return field if re.match(pattern, field) else None #netchikiw idha warning nkhaliwha non, idha error (mandatory) -> error

#fixme: move later to utils file
def is_valid_email(field: str):
    return field if is_regex_matched(email_regex, field) else None

def is_positive_int(field: str):
    try:
        res = int(field)
    except:
        return None # not parsable to int
    
    return res if res >= 0 else None

def is_valid_date(field: str):
    try:
        #FIXME: try to give the user the possibility to configure dates format
        # or try many format (not recommended) 12/01 -> 12 jan
        # 12/01 -> mm/dd -> 1 dec
        # user we3i bel format
        obj = datetime.strptime(field, '%Y-%m-%d')
        return obj.isoformat()
    except:
        return None # fchel enou yrodha date -> not parsable to int
    
def isCdiOrCdd(employee):
    return employee["contract_type"].value in [enums.ContractType.Cdi, enums.ContractType.Cdd]

def is_valid_cnss_number(field):
    return field if is_regex_matched(cnss_regex, field) else None
    # idha mch shyh ama type contract mch cdi, cdd => warning
    # => error

def is_valid_phone_number(field):
    return field if is_regex_matched(phone_number_regex, field) else None

def are_roles_valid(field):
    # Admin,  venDor,  
    res = []
    for role_name in field.split(','):
        val = enums.RoleType.is_valid_enum_value(role_name)
        if not val:
            return None
        res.append(val)

    return res # [enums.RoleType.Admin, enums.RoleType.Vendor]
        


fields_check = {
    # field to validate: (function to validate, error message if not valid)
    "email": (lambda field: is_valid_email(field), "Wrong Email format"),
    "gender": (lambda field: enums.Gender.is_valid_enum_value(field), f"Possible values are: { enums.Gender.getPossibleValues() }"),
    "contract_type": (lambda field: enums.ContractType.is_valid_enum_value(field), f"Possible values are: { enums.ContractType.getPossibleValues() }"),
    "number": (lambda field: is_positive_int(field), "It Should be an integer >= 0"),
    "birth_date": (lambda field: is_valid_date(field), "Dates format should be dd/mm/YYYY"),
    "cnss_number": (lambda field: is_valid_cnss_number(field), "It should be {8 digits}-{2 digits} and it's Mandatory for Cdi and Cdd"),
    "phone_number": (lambda field: is_valid_phone_number(field), "Phone number is not valid for tunisia, it shoud be of 8 digits"),
    "employee_roles": (lambda field: are_roles_valid(field), f"Possible values are: { enums.RoleType.getPossibleValues() }"),
}

def is_field_mandatory(employee, field):
    return field in mandatory_fields or (field in mandatory_with_condition and mandatory_with_condition[field][1](employee))

#employee wehed 
def validate_employee_data(employee):
    errors = []
    warnings = []
    wrong_cells = []  # bech nraj3ouhom ll matchy ylawanhom bel a7mer
    employee_to_add = { field: cell.value for field, cell in employee.items() }

    for field in possible_fields:
        if field not in employee:
            if is_field_mandatory(employee, field):
                errors.append(f"{possible_fields[field]} is mandatory but missing")
            continue

        cell = employee[field]
        employee_to_add[field] = employee_to_add[field].strip()

        if employee_to_add[field] == '': #birth date optional = ""
            if is_field_mandatory(employee, field):
                msg = f"{possible_fields[field][0]} is mandatory but missing"
                errors.append(msg)
                wrong_cells.append(schemas.MatchyWrongCell(message=msg, rowIndex=cell.rowIndex, colIndex=cell.colIndex))
            else:
                employee_to_add[field] = None # f db tetsab null
        elif field in fields_check:
            converted_val = fields_check[field][0](employee_to_add[field])
            if converted_val is None: #if not convered_val khater ken je 3ana type bool => False valid value, int >= 0 converted_val = 0
                msg = fields_check[field][1]
                (errors if is_field_mandatory(employee, field) else warnings).append(msg)
                wrong_cells.append(schemas.MatchyWrongCell(message=msg, rowIndex=cell.rowIndex, colIndex=cell.colIndex))
            else:
                employee_to_add[field] = converted_val

    return (errors, warnings, wrong_cells, employee_to_add)

def valid_employees_data_and_upload(employees: list, force_upload: bool, backgroundTasks: BackgroundTasks, db: DbDep):
    #try:
        errors = []
        warnings = []
        wrong_cells = []
        employees_to_add = [] # bech nesta3mlou fil batch add, bech nlemou data lkol w nsobo fard mara
        roles_per_email = {}
        
        roles = []
        for line, employee in enumerate(employees): # for i in range(len(employees))  line = i, employee = employees[i]
            emp_errors, emp_warnings, emp_wrong_cells, emp = validate_employee_data(employee)
            if emp_errors:
                msg = ('\n').join(emp_errors)
                errors.append(f"\nLine {line + 1}: \n{msg}")
            if emp_warnings:
                msg = ('\n').join(emp_warnings)
                warnings.append(f"\nLine {line + 1}: \n{msg}")
            if emp_wrong_cells:
                wrong_cells.extend(emp_wrong_cells)
            
            roles_per_email[emp.get('email')] = emp.pop('employee_roles') #email unique
            emp['password'] = uuid.uuid1()
            employees_to_add.append(models.Employee(**emp))
        
        for field in unique_fields:
            values = set()
            for line, employee in enumerate(employees):
                cell = employee.get(field)
                val = cell.value.strip()
                if val == '': # if it's mandatory, email and number were already checked in fields check
                    continue
                if val in values:
                    msg = f"{possible_fields[field]} should be unique. but this value exists more than one time in the file"
                    (errors if is_field_mandatory(employee, field) else warnings).append(msg)
                    wrong_cells.append(schemas.MatchyWrongCell(message=msg, rowIndex=cell.rowIndex, colIndex=cell.colIndex))
                else:
                    values.add(val)

            duplicated_vals = db.query(unique_fields[field]).filter(unique_fields[field].in_(values)).all()
            duplicated_vals = {str(val[0]) for val in duplicated_vals}
            if duplicated_vals:
                msg = f"{possible_fields[field]} should be unique. {(', ').join(duplicated_vals)} already exist in database"
                (errors if is_field_mandatory(employee, field) else warnings).append(msg)
                for employee in employees:
                    cell = employee.get(field)
                    val = cell.value.strip()

                    if val in duplicated_vals:
                        wrong_cells.append(schemas.MatchyWrongCell(message=f"{possible_fields[field]} should be unique. {val} already exist in database", rowIndex=cell.rowIndex, colIndex=cell.colIndex))
        
        if errors or (warnings and not force_upload): # oumourou l force mayet3adech idha errors w yet3ada idha warning ama lezem force_upload = True
            return schemas.ImportResponse(
                errors=('\n').join(errors),
                warnings=('\n').join(warnings),
                wrong_cells=wrong_cells,
                detail="something went wrong",
                status_code=400,
            )
        # exercice: add
        # add_all vs nektbou l query wahadna w laken rod belek w hawel esta3mel l orm le max
        # n7ebou naarfou role kol user  baed maysirlou add
        db.add_all(employees_to_add)
        db.flush() # field id fih value, email mawjoud
        #case 1: imagine employees lost their order
        employee_roles = []
        for emp in employees_to_add:
            for role in roles_per_email[emp.email]:
                employee_roles.append(models.EmployeeRole(employee_id=emp.id, role=role))

        db.add_all(employee_roles)
        db.flush()

        activation_codes_to_add = []
        email_data = []
        for emp in employees_to_add:
            token = uuid.uuid1()
            activation_code = models.AccountActivation(employee_id=emp.id, email=emp.email, status=enums.TokenStatus.Pending, token=token)
            activation_codes_to_add.append(activation_code)
            email_data.append(([emp.email], {
                'name': emp.first_name,
                'code': token,
                'psw': emp.password
            }))

        db.add_all(activation_codes_to_add)

        # choice 1, wait for the sending (takes time, in case of problem, we rollback all transactions)
        for email_datum in email_data:
            backgroundTasks.add_task(emailService.simple_send, email_datum[0], email_datum[1])

        # choice 2, do it using background tasks, if failed, no problem add a btn 'you haven't received an email ? send again'


        db.commit()

    # except Exception as e:
    #     db.rollback()
    #     text = str(e)
    #     add_error(text, db) #   
    #     raise HTTPException(status_code=500, detail=get_error_message(text, error_keys))

        return schemas.ImportResponse(
            detail="file uploaded",
            status_code=201
        )

def add_error(text, db):
    try:
        db.add(models.Error(
            text=text,
        ))
        db.commit()
    except Exception as e:
        # alternative solutions bech ken db tahet najem nal9a l mochkla
        raise HTTPException(status_code=500, detail="Something went wrong")      

def get_error_message(error_message, error_keys):
    for error_key in error_keys:
        if error_key in error_message:
            return error_keys[error_key]
        
    return "Something went wrong"

@app.get("/possibleFields")
def getPossibleFields(db: DbDep):
    return schemas.ImportPossibleFields(
        possible_fields=options,
    )

@app.post('/test')
async def upload(entry: schemas.MatchyUploadEntry, backgroundTasks: BackgroundTasks, db: DbDep):
    employees = entry.lines
    if not employees: # front lezmou ygeri enou fama au moins ligne
        return schemas.BaseOut(status_code=400, detail="Nothing to do, empty file")

    missing_mandatory_fields = set(mandatory_fields.keys()) - employees[0].keys() # 3tina thi9a f matchy eli input valid
    if missing_mandatory_fields:
        return schemas.BaseOut(
            status_code=400, 
            detail=f"missing mandatory fields: {(', ').join([mandatory_fields[field] for field in missing_mandatory_fields])}"
        )
    
    return valid_employees_data_and_upload(employees, entry.forceUpload, backgroundTasks, db)
