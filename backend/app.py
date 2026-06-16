import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import text

# Import the db instance and models
from models import db, Session, Document, Chunk

load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app) # Allows your Vite React frontend to talk to Flask
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        # Ensure pgvector extension is created before building tables
        db.session.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        db.session.commit()
        db.create_all()

    # --- API ROUTES ---

    @app.route('/api/sessions', methods=['POST'])
    def create_session():
        data = request.json
        new_session = Session(name=data.get('name', 'Untitled Session'))
        db.session.add(new_session)
        db.session.commit()
        return jsonify({"session_id": new_session.id, "name": new_session.name}), 201

    @app.route('/api/sessions/<session_id>/upload', methods=['POST'])
    def upload_documents(session_id):
        # Placeholder for Phase 2: Ingestion Logic
        # 1. Receive files via request.files
        # 2. Extract text (PDF/Excel -> Pandas/OCR)
        # 3. Save to Document model
        # 4. Chunk text, Embed, save to Chunk model
        return jsonify({"message": f"Upload route ready for session {session_id}"}), 200

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)