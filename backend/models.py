from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Session(db.Model):
    __tablename__ = 'sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Cascade delete ensures deleting a session removes all associated metadata files
    documents = db.relationship('Document', backref='session', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat()
        }

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)  # 'pdf', 'xlsx', 'csv'
    filepath = db.Column(db.String(512), nullable=False)  # Physical path on disk/storage
    status = db.Column(db.String(50), default="uploaded")  # 'uploaded', 'processing', 'completed', 'failed'
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "filename": self.filename,
            "filetype": self.filetype,
            "filepath": self.filepath,
            "status": self.status,
            "uploaded_at": self.uploaded_at.isoformat()
        }