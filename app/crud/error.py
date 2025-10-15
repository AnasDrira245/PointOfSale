from fastapi import HTTPException
from app import models

def get_error_message(error_message, error_keys):
    for error_key in error_keys:
        if error_key in error_message:
            return error_keys[error_key]
        
    return "Something went wrong"

def add_error(text, db):
    try:
        db.add(models.Error(
            text=text,
        ))
        db.commit()
    except Exception as e:
        # alternative solutions bech ken db tahet najem nal9a l mochkla
        raise HTTPException(status_code=500, detail="Something went wrong") 