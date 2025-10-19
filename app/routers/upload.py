from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.document import Document
import mimetypes
import pdfplumber

router = APIRouter(prefix="/api/v1/upload")

@router.post("")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_name = file.filename
    file_mime_type = mimetypes.guess_type(file.filename)[0]
    extracted_file_content = ""

    for page in pdfplumber.open(file.file).pages:
        extracted_file_content += page.extract_text()

    document = Document(filename=file_name, mime_type=file_mime_type, raw_text=extracted_file_content, embedding=None)
    db.add(document)
    db.commit()

    return {"message": "File uploaded successfully", "document_name": document.filename}