from pathlib import Path
from typing import List
from fastapi import BackgroundTasks, FastAPI
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from starlette.responses import JSONResponse
from .config import settings
from . import schemas

conf = ConnectionConfig(
    MAIL_USERNAME =settings.mail_username,
    MAIL_PASSWORD = settings.mail_password,
    MAIL_FROM = settings.mail_from,
    MAIL_PORT=465,
    MAIL_SERVER = settings.mail_server, 
    MAIL_STARTTLS = False,
    MAIL_SSL_TLS = True,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True,
    TEMPLATE_FOLDER = Path(__file__).parent / 'templates',
)



html = """
<p>Thanks for using Fastapi-mail</p> 
"""

async def simple_send(email: schemas.EmailSchema) -> JSONResponse:
    message = MessageSchema(
        subject="Fastapi-Mail module",
        recipients=email.dict().get("email"),
        template_body=email.dict().get("body"),
        subtype=MessageType.html)

    fm = FastMail(conf)
    await fm.send_message(message,template_name="account_activation.html")
    return JSONResponse(status_code=200, content={"message": "email has been sent"})    
