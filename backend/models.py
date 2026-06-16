from flask_sqlalchemy import SQLAlchemy
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

db = SQLAlchemy()

class Session(db.Model):
    __tablename__ = 'sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(150), nullable=True) # e.g., "Morgan Stanley Q3 Tender"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to documents
    documents = db.relationship('Document', backref='session', lazy=True, cascade="all, delete-orphan")

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False) # 'pdf', 'excel', etc.
    extracted_text = db.Column(db.Text, nullable=True) # The raw, full text for hydration
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to chunks
    chunks = db.relationship('Chunk', backref='document', lazy=True, cascade="all, delete-orphan")

class Chunk(db.Model):
    __tablename__ = 'chunks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False)
    page_number = db.Column(db.Integer, nullable=True) # Useful for referencing the exact page
    text_content = db.Column(db.Text, nullable=False)
    
    # Vector column. The dimension size (e.g., 384 or 1536) depends on your chosen embedding model.
    # We will use 384 as a placeholder for a lightweight local model like all-MiniLM-L6-v2.
    embedding = db.Column(Vector(384))