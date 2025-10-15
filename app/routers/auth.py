from app import models, enums
from app import schemas
from app.OAuth2 import ACCESS_TOKEN_EXPIRE_MINUTES, authenticate_employee, create_access_token, get_password_hash
from app.crud.auth import add_reset_code, edit_confirmation_code, edit_reset_code, get_confirmation_code, get_reset_code
from app.crud.employee import sudo_edit_employee, get_employee_by_email
from app.crud.error import add_error, get_error_message
from app.dependencies import DbDep, formDataDep

from fastapi import APIRouter, HTTPException, status

from app.external_services import emailService
from datetime import datetime, timedelta

app = APIRouter(
    tags=["Authentication"],
)

#fixme later
error_keys = {}

@app.post("/token")
async def login(db: DbDep, form_data: formDataDep):
    try:
        employee = authenticate_employee(db, form_data.username, form_data.password)
        if not employee:
                raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if employee.account_status == enums.AccountStatus.Inactive:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email has not been verified yet",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data = {
                "email": employee.email, 
                "roles": [emp_role.role.value for emp_role in employee.roles]
            }, 
            expires_delta = access_token_expires
        )
    except Exception as e:
        db.rollback()
        text = str(e)
        add_error(text, db)
        return schemas.BaseOut(status_code=500, detail=text)
    
    return schemas.Token(access_token=access_token, token_type="bearer", detail="Welcome, you're logged in", status_code = 200)

@app.patch("/confirmAccount", response_model=schemas.BaseOut)
def confirm_account(confirAccountInput: schemas.ConfirmAccount, db: DbDep):
    try:
        confirmation_code = get_confirmation_code(db, confirAccountInput.confirmation_code)

        if not confirmation_code:
            return schemas.BaseOut(status_code=400, detail="token does not exist")
        
        if confirmation_code.status == enums.TokenStatus.Used:
            return schemas.BaseOut(status_code=400, detail="token already used")
        
        diff = (datetime.now() - confirmation_code.created_on).seconds

        if diff > 3600:
            return schemas.BaseOut(status_code=400, detail="token expired")

        # employee become active => he can start using the app
        sudo_edit_employee(db, confirmation_code.employee_id, {models.Employee.account_status: enums.AccountStatus.Active})

        # token used => you cannot use it again (to test mahmoud)
        edit_confirmation_code(db, confirmation_code.id, {models.AccountActivation.status: enums.TokenStatus.Used})

        db.commit()
    except Exception as e:
        db.rollback()
        text = str(e)
        add_error(text, db)
        return schemas.BaseOut(status_code=500, detail=get_error_message(text, error_keys))
        
    return schemas.BaseOut(
        detail = "Account confirmed",
        status_code = status.HTTP_200_OK
    )

@app.post('/forgotPassword', response_model = schemas.BaseOut)
async def forgot_password(entry: schemas.ForgetPassword, db: DbDep):
    employee = get_employee_by_email(db, entry.email)
    if not employee:
        return schemas.BaseOut(
            detail = "No account with this email",
            status_code = status.HTTP_404_NOT_FOUND
        )
    try:
        reset_code = add_reset_code(db, employee)
        db.flush()
        await emailService.simple_send([employee.email], {
                'name': employee.first_name,
                'code': reset_code.token,
            }, enums.EmailTemplate.ResetPassword,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        text = str(e)
        add_error(text, db)
        return schemas.BaseOut(status_code=500, detail=get_error_message(text, error_keys)) 
        
    return schemas.BaseOut(
        detail="email sent!",
        status_code=status.HTTP_200_OK
    )

@app.patch("/resetPassword", response_model=schemas.BaseOut)
def reset_password(entry: schemas.ResetPassword, db: DbDep):
    try:
        reset_code = get_reset_code(db, entry.reset_code)

        if not reset_code:
            return schemas.BaseOut(status_code=400, detail="token does not exist")
        
        if reset_code.status == enums.TokenStatus.Used:
            return schemas.BaseOut(status_code=400, detail="token already used")
        
        diff = (datetime.now() - reset_code.created_on).seconds

        if diff > 3600:
            return schemas.BaseOut(status_code=400, detail="token expired")
        
        if entry.password != entry.confirm_password:
            return schemas.BaseOut(status_code=400, detail="passwords do not match")
        
        sudo_edit_employee(db, reset_code.employee_id, {models.Employee.password: get_password_hash(entry.password)})
        # token used => you cannot use it again (to test mahmoud)
        edit_reset_code(db, reset_code.id, {models.ResetPassword.status: enums.TokenStatus.Used})

        db.commit()
    except Exception as e:
        db.rollback()
        text = str(e)
        add_error(text, db)
        return schemas.BaseOut(status_code=500, detail=get_error_message(text, error_keys))
        
    return schemas.BaseOut(
        detail = "Password changed",
        status_code = status.HTTP_200_OK
    )
