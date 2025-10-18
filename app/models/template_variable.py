# Template variables model
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from app.db.base import Base


class TemplateVariable(Base):
    __tablename__ = "template_variable"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("template.id", ondelete="CASCADE"), nullable=False)
    key = Column(String, nullable=False)
    label = Column(String, nullable=False)
    description = Column(Text)
    example = Column(String)
    required = Column(Boolean, default=False)
    dtype = Column(String, default="string")
    regex = Column(String)
    enum_values = Column(ARRAY(String))

    def to_dict(self):
        return {
            "id": self.id,
            "template_id": self.template_id,
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "example": self.example,
            "required": self.required,
            "dtype": self.dtype,
            "regex": self.regex,
            "enum_values": self.enum_values,
        }

