from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY, JSON, Float
from sqlalchemy.sql import func
from app.db.base import Base


class Template(Base):
    __tablename__ = "template"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    file_description = Column(Text)
    doc_type = Column(String)
    jurisdiction = Column(String)
    similarity_tags = Column(ARRAY(String))
    body_md = Column(Text, nullable=False)
    metadata = Column(JSON)
    embedding = Column(ARRAY(Float))  # Store embedding as array
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "template_id": self.template_id,
            "title": self.title,
            "file_description": self.file_description,
            "doc_type": self.doc_type,
            "jurisdiction": self.jurisdiction,
            "similarity_tags": self.similarity_tags,
            "body_md": self.body_md,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

