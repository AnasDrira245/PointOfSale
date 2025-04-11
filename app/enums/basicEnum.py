
from enum import Enum

class BasicEnum(str,Enum):

    @classmethod
    def getPossibleValues(cls):
        return [val.value for val in cls]
    
    def is_valid_enum_value(cls,filed):
        for val  in cls:
            if val.value.upper() == filed.strip().upper():
                return val
            
        return None
    
    