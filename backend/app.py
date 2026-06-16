import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Import models and database configuration
from models import db, Session, Document

load_dotenv()

# Configuration for local document uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storage')
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enables cross-origin requests from the React development server
    
    # Configuration strings
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    print("DATABASE_URL =", os.getenv("DATABASE_URL"))
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    # --- SESSIONS API ---

    @app.route('/api/sessions', methods=['POST'])
    def create_session():
        data = request.json or {}
        if not data.get('name'):
            return jsonify({"error": "Session name is required"}), 400
            
        new_session = Session(
            name=data.get('name'),
            description=data.get('description')
        )
        db.session.add(new_session)
        db.session.commit()
        return jsonify(new_session.to_dict()), 201

    @app.route('/api/sessions', methods=['GET'])
    def get_sessions():
        sessions = Session.query.order_by(Session.created_at.desc()).all()
        return jsonify([s.to_dict() for s in sessions]), 200

    @app.route('/api/sessions/<id>', methods=['DELETE'])
    def delete_session(id):
        session_obj = Session.query.get(id)
        if not session_obj:
            return jsonify({"error": "Session not found"}), 404
            
        # Optional manual step: You could physically remove files linked to documents here
        db.session.delete(session_obj)
        db.session.commit()
        return jsonify({"message": f"Session {id} successfully deleted"}), 200

    # --- DOCUMENTS API ---

    @app.route('/api/documents', methods=['POST'])
    def upload_document():
        # Check if the multipart form-data has the required fields
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
            
        file = request.files['file']
        session_id = request.form.get('session_id')
        
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
            
        # Verify parent session exists
        if not Session.query.get(session_id):
            return jsonify({"error": "Target session does not exist"}), 404

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filetype = filename.rsplit('.', 1)[1].lower()
            
            # Save the file locally using a unique name prefix to avoid overwrites
            unique_filename = f"{session_id}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Track metadata within PostgreSQL
            new_doc = Document(
                session_id=session_id,
                filename=filename,
                filetype=filetype,
                filepath=filepath,
                status="uploaded"
            )
            db.session.add(new_doc)
            db.session.commit()
            
            return jsonify(new_doc.to_dict()), 201
            
        return jsonify({"error": "File extension not allowed"}), 400

    @app.route('/api/documents/<sessionId>', methods=['GET'])
    def get_documents_by_session(sessionId):
        # Verify session existence
        if not Session.query.get(sessionId):
            return jsonify({"error": "Session not found"}), 404
            
        documents = Document.query.filter_by(session_id=sessionId).all()
        return jsonify([d.to_dict() for d in documents]), 200

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)