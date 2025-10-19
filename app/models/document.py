# Documents model
from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY, Float, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class Document(Base):
    __tablename__ = "document"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    raw_text = Column(Text)
    document_metadata = Column(JSON)
    embedding = Column(ARRAY(Float))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "document_metadata": self.document_metadata,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

