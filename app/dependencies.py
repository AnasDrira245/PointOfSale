from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.OAuth2 import get_curr_employee
from .database import get_db
from sqlalchemy.orm import Session  

DbDep = Annotated[Session, Depends(get_db)]

class PagiantionParams:
    def __init__(self, page_size: int = 10, page_number: int = 1):
        self.page_size = page_size
        self.page_number = page_number

paginationParams = Annotated[PagiantionParams, Depends()]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

tokenDep = Annotated[str, Depends(oauth2_scheme)]

formDataDep = Annotated[OAuth2PasswordRequestForm, Depends()]

def get_current_employee(db: DbDep, token: tokenDep):
    return get_curr_employee(db, token)

currentEmployee = Annotated[any, Depends(get_current_employee)]
