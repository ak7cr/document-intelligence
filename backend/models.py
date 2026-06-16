from datetime import datetime, timezone
import uuid

def _now() -> datetime:
    return datetime.now(timezone.utc)

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Session(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_now)

    documents = db.relationship(
        "Document", backref="session", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), db.ForeignKey("sessions.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    bucket = db.Column(db.String(100), nullable=True)
    object_key = db.Column(db.String(512), nullable=True)
    filepath = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(50), default="uploaded")
    uploaded_at = db.Column(db.DateTime, default=_now)

    text = db.relationship(
        "DocumentText",
        backref="document",
        uselist=False,
        cascade="all, delete-orphan",
    )
    chunks = db.relationship(
        "DocumentChunk",
        backref="document",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )

    def to_dict(self) -> dict:
        data: dict = {
            "id": self.id,
            "session_id": self.session_id,
            "filename": self.filename,
            "filetype": self.filetype,
            "bucket": self.bucket,
            "object_key": self.object_key,
            "status": self.status,
            "uploaded_at": self.uploaded_at.isoformat(),
            "word_count": None,
            "page_count": None,
            "chunk_count": len(self.chunks),
        }
        if self.text:
            data["word_count"] = self.text.word_count
            data["page_count"] = self.text.page_count
        return data


class DocumentText(db.Model):
    __tablename__ = "document_text"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(
        db.String(36),
        db.ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    raw_text = db.Column(db.Text, nullable=False, default="")
    page_count = db.Column(db.Integer, nullable=True)
    word_count = db.Column(db.Integer, nullable=False, default=0)
    method = db.Column(db.String(50), default="direct")  # 'direct' | 'ocr' | 'ocr_pending'
    ocr_confidence = db.Column(db.Float, nullable=True)  # 0.0–1.0, None for direct
    extracted_at = db.Column(db.DateTime, default=_now)

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "word_count": self.word_count,
            "page_count": self.page_count,
            "method": self.method,
            "extracted_at": self.extracted_at.isoformat(),
        }


class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(
        db.String(36),
        db.ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    token_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=_now)

    __table_args__ = (
        db.Index("ix_chunks_doc", "document_id"),
        db.UniqueConstraint("document_id", "chunk_index", name="uq_chunk"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "token_count": self.token_count,
        }
