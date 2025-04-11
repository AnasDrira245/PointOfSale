from datetime import date,datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr
from app.enums import ContractType,Gender,AccountStatus,RoleType
from app.enums.matchyComparer import Comparer
from app.enums.matchyConditionProprety import ConditionProperty
from app.enums.matchyFieldType import FieldType

class OurBaseModel(BaseModel):
    class Config:
        orm_mode=True

class EmployeeBase(OurBaseModel):
    first_name:str
    last_name:str
    email:str
    number:int
    birth_date:date | None=None
    address:str | None=None
    cnss_number:str|None=None
    contract_type:ContractType
    gender:Gender
    roles:List[RoleType]
    phone_number:str | None=None
  

class EmployeeCreate(EmployeeBase):
    password:str | None=None
    confirm_password:str | None=None


class EmployeeOut(EmployeeBase):
    id :int
    created_on:datetime

    
class EmailSchema(OurBaseModel):
    email: List[EmailStr]
    body: Dict[str, Any]


class ConfimAccount(OurBaseModel):
    confirmation_code:str   

class BaseOut(OurBaseModel):
    detail:str
    status_code:int


class MatchyCondition(OurBaseModel):
    proprety:ConditionProperty
    comparer:Optional[Comparer] = None
    value : int | float | str | list[str]
    custom_fail_message : Optional[str] = None



class MatchyOption(OurBaseModel):
    display_value:str
    value : Optional[str] = None
    mandatory:Optional[bool] = False
    type:FieldType 
    conditions:Optional[List[MatchyCondition]] = []
    
class ImportPossibleFields(OurBaseModel):
    possibleFields:List[MatchyOption]=[]


class MatchyCell(OurBaseModel):
    value:str
    rowIndex:int
    colIndex:int

class MatchyUploadEntry(OurBaseModel):
    lines:List[Dict[str,MatchyCell]]


class MatchyWrongCell(OurBaseModel):
    message:str
    rowIndex:int
    colIndex:int


class ImportResponse(OurBaseModel):
    errors:str
    warnings:str 
    wrong_cells:list[MatchyWrongCell]