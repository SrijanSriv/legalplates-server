# Draft instances model
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class Instance(Base):
    __tablename__ = "instance"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("template.id", ondelete="SET NULL"))
    user_query = Column(Text, nullable=False)
    answers_json = Column(JSON)
    draft_md = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "template_id": self.template_id,
            "user_query": self.user_query,
            "answers_json": self.answers_json,
            "draft_md": self.draft_md,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

