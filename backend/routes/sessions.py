from flask import Blueprint, jsonify, request

from models import CompanyProfile, Session, db
from storage import delete_file
from vector import search_chunks

OCR_CONFIDENCE_THRESHOLD = 0.70

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/sessions", methods=["POST"])
def create_session():
    data = request.json or {}
    if not data.get("name"):
        return jsonify({"error": "Session name is required"}), 400
    session = Session(name=data["name"], description=data.get("description"))
    db.session.add(session)
    db.session.commit()
    return jsonify(session.to_dict()), 201


@sessions_bp.route("/sessions", methods=["GET"])
def get_sessions():
    sessions = Session.query.order_by(Session.created_at.desc()).all()
    return jsonify([s.to_dict() for s in sessions]), 200


@sessions_bp.route("/sessions/<session_id>/search", methods=["GET"])
def search_session(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    limit = min(int(request.args.get("limit", 5)), 20)
    results = search_chunks(q, session_id=session_id, top_k=limit)
    return jsonify({"query": q, "results": results}), 200


@sessions_bp.route("/sessions/<session_id>/analytics", methods=["GET"])
def session_analytics(session_id: str):
    from collections import Counter
    from models import Document, DocumentChunk, DocumentEntity, DocumentText

    session = Session.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    docs = Document.query.filter_by(session_id=session_id).order_by(Document.uploaded_at).all()

    # ── Totals ────────────────────────────────────────────────────────────────
    status_counts: dict[str, int] = Counter(d.status for d in docs)  # type: ignore[assignment]
    total_pages = 0
    total_words = 0
    total_chunks = 0
    for doc in docs:
        dt = DocumentText.query.filter_by(document_id=doc.id).first()
        if dt:
            total_pages += dt.page_count or 0
            total_words += dt.word_count or 0
        total_chunks += DocumentChunk.query.filter_by(document_id=doc.id).count()

    all_entities = DocumentEntity.query.filter(
        DocumentEntity.document_id.in_([d.id for d in docs])
    ).all()

    # ── Breakdowns ────────────────────────────────────────────────────────────
    filetype_counts: dict[str, int] = Counter(d.filetype for d in docs)  # type: ignore[assignment]
    entity_type_counts: dict[str, int] = Counter(e.entity_type for e in all_entities)  # type: ignore[assignment]

    # Top entities per type (max 5 per type)
    top_entities: dict[str, list[dict]] = {}
    for etype in entity_type_counts:
        if etype == "doc_type":
            continue
        vals: list[str] = [e.value for e in all_entities if e.entity_type == etype]
        top: list[dict] = [{"value": v, "count": c} for v, c in Counter(vals).most_common(5)]
        if top:
            top_entities[etype] = top

    # ── Upload timeline (by date) ──────────────────────────────────────────────
    date_counts: dict[str, int] = Counter(  # type: ignore[assignment]
        d.uploaded_at.strftime("%Y-%m-%d") for d in docs
    )
    timeline = [{"date": k, "count": v} for k, v in sorted(date_counts.items())]

    return jsonify({
        "session_id": session_id,
        "session_name": session.name,
        "totals": {
            "documents": len(docs),
            "ready": status_counts.get("ready", 0),
            "processing": status_counts.get("processing", 0) + status_counts.get("uploaded", 0),
            "failed": status_counts.get("failed", 0),
            "pages": total_pages,
            "words": total_words,
            "chunks": total_chunks,
            "entities": len(all_entities),
        },
        "doc_types": dict(filetype_counts),
        "entity_types": dict(entity_type_counts),
        "top_entities": top_entities,
        "timeline": timeline,
    }), 200


@sessions_bp.route("/sessions/<session_id>/compare", methods=["POST"])
def compare_session_docs(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    data = request.json or {}
    doc_ids = data.get("doc_ids", [])
    if len(doc_ids) < 2:
        return jsonify({"error": "At least 2 doc_ids required"}), 400
    try:
        from compare import compare_documents
        result = compare_documents(doc_ids)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "Comparison failed", "detail": str(exc)}), 500


@sessions_bp.route("/sessions/<session_id>/profile", methods=["GET"])
def get_profile(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    profile = CompanyProfile.query.filter_by(session_id=session_id).first()
    if not profile:
        return jsonify({"error": "No profile set up for this session"}), 404
    return jsonify(profile.to_dict()), 200


@sessions_bp.route("/sessions/<session_id>/profile", methods=["POST"])
def upsert_profile(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    data = request.json or {}
    profile = CompanyProfile.query.filter_by(session_id=session_id).first()
    if profile:
        profile.company_name = data.get("company_name", profile.company_name)
        profile.annual_turnover = data.get("annual_turnover", profile.annual_turnover)
        profile.years_in_business = data.get("years_in_business", profile.years_in_business)
        profile.certifications = data.get("certifications", profile.certifications)
        profile.similar_projects = data.get("similar_projects", profile.similar_projects)
        profile.employee_count = data.get("employee_count", profile.employee_count)
        profile.extra_details = data.get("extra_details", profile.extra_details)
    else:
        profile = CompanyProfile(
            session_id=session_id,
            company_name=data.get("company_name", ""),
            annual_turnover=data.get("annual_turnover", ""),
            years_in_business=data.get("years_in_business"),
            certifications=data.get("certifications", []),
            similar_projects=data.get("similar_projects"),
            employee_count=data.get("employee_count", ""),
            extra_details=data.get("extra_details", ""),
        )
        db.session.add(profile)
    db.session.commit()
    return jsonify(profile.to_dict()), 200


@sessions_bp.route("/sessions/<session_id>/ocr-review", methods=["GET"])
def ocr_review(session_id: str):
    from models import Document, DocumentText

    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    docs = Document.query.filter_by(session_id=session_id, status="ready").all()
    items = []
    for doc in docs:
        dt = DocumentText.query.filter_by(document_id=doc.id).first()
        if not dt or dt.method != "ocr":
            continue
        confidence = dt.ocr_confidence
        if confidence is None or confidence < OCR_CONFIDENCE_THRESHOLD:
            items.append({
                "document_id": doc.id,
                "filename": doc.filename,
                "method": dt.method,
                "ocr_confidence": confidence,
                "page_count": dt.page_count,
                "word_count": dt.word_count,
            })

    items.sort(key=lambda x: (x["ocr_confidence"] or 0.0))
    return jsonify({"session_id": session_id, "items": items, "threshold": OCR_CONFIDENCE_THRESHOLD}), 200


@sessions_bp.route("/sessions/<session_id>/entity-graph", methods=["GET"])
def entity_graph(session_id: str):
    from collections import defaultdict
    from models import Document, DocumentEntity

    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    docs = Document.query.filter_by(session_id=session_id, status="ready").all()
    if not docs:
        return jsonify({"session_id": session_id, "clusters": [], "total_shared": 0}), 200

    doc_map = {d.id: d.filename for d in docs}
    doc_ids = list(doc_map.keys())

    entities = DocumentEntity.query.filter(
        DocumentEntity.document_id.in_(doc_ids),
        DocumentEntity.entity_type != "doc_type",
    ).all()

    # Group by (type, normalized value)
    groups: dict[tuple, list] = defaultdict(list)
    for e in entities:
        key = (e.entity_type, e.value.lower().strip())
        groups[key].append(e)

    clusters = []
    for (etype, _), ents in groups.items():
        unique_docs = {e.document_id for e in ents}
        if len(unique_docs) < 2:
            continue
        doc_entries = []
        seen = set()
        for e in ents:
            if e.document_id not in seen:
                seen.add(e.document_id)
                doc_entries.append({
                    "id": e.document_id,
                    "filename": doc_map.get(e.document_id, ""),
                    "label": e.label,
                })
        clusters.append({
            "entity_type": etype,
            "value": ents[0].value,
            "doc_count": len(unique_docs),
            "documents": doc_entries,
        })

    clusters.sort(key=lambda x: (-x["doc_count"], x["entity_type"]))

    return jsonify({
        "session_id": session_id,
        "clusters": clusters,
        "total_shared": len(clusters),
    }), 200


@sessions_bp.route("/sessions/<session_id>/run-analysis", methods=["POST"])
def run_session_analysis(session_id: str):
    """Agentic: run checklist + eligibility on all ready docs that haven't been checked yet."""
    from models import CompanyProfile, Document, DocumentChecklist, DocumentText, EligibilityCheck

    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    docs = Document.query.filter_by(session_id=session_id, status="ready").all()
    profile = CompanyProfile.query.filter_by(session_id=session_id).first()

    checklist_count = 0
    eligibility_count = 0
    errors = []

    for doc in docs:
        dt = DocumentText.query.filter_by(document_id=doc.id).first()
        if not dt:
            continue

        # Checklist
        existing_cl = DocumentChecklist.query.filter_by(document_id=doc.id).first()
        if not existing_cl:
            try:
                from checklist import build_checklist
                from models import db
                cl_result = build_checklist(dt.raw_text)
                db.session.add(DocumentChecklist(document_id=doc.id, items=cl_result["items"]))
                db.session.commit()
                checklist_count += 1
            except Exception as exc:
                db.session.rollback()
                errors.append(f"{doc.filename}: checklist failed — {exc}")

        # Eligibility
        if profile:
            existing_elig = EligibilityCheck.query.filter_by(document_id=doc.id).first()
            if not existing_elig:
                try:
                    from eligibility import check_eligibility
                    from models import db
                    elig_result = check_eligibility(dt.raw_text, profile.to_dict())
                    db.session.add(EligibilityCheck(document_id=doc.id, profile_id=profile.id, **elig_result))
                    db.session.commit()
                    eligibility_count += 1
                except Exception as exc:
                    db.session.rollback()
                    errors.append(f"{doc.filename}: eligibility failed — {exc}")

    return jsonify({
        "checklist_run": checklist_count,
        "eligibility_run": eligibility_count,
        "errors": errors,
    }), 200


@sessions_bp.route("/sessions/<session_id>/timeline", methods=["GET"])
def session_timeline(session_id: str):
    from datetime import date, datetime
    from models import Document, DocumentEntity

    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    docs = Document.query.filter_by(session_id=session_id, status="ready").all()
    doc_map = {d.id: d.filename for d in docs}

    entities = DocumentEntity.query.filter(
        DocumentEntity.document_id.in_(list(doc_map.keys())),
        DocumentEntity.entity_type.in_(["date", "deadline"]),
    ).all()

    today = date.today()
    items = []
    for ent in entities:
        parsed_date = None
        try:
            from dateutil import parser as dateparser
            parsed_date = dateparser.parse(
                ent.value,
                default=datetime(today.year, today.month, today.day),
            ).date()
        except Exception:
            pass

        days_from_now = None
        urgency = "unknown"
        if parsed_date:
            days_from_now = (parsed_date - today).days
            if days_from_now < 0:
                urgency = "past"
            elif days_from_now <= 7:
                urgency = "critical"
            elif days_from_now <= 30:
                urgency = "soon"
            else:
                urgency = "future"

        items.append({
            "entity_id": ent.id,
            "document_id": ent.document_id,
            "filename": doc_map.get(ent.document_id, ""),
            "label": ent.label,
            "value": ent.value,
            "entity_type": ent.entity_type,
            "parsed_date": parsed_date.isoformat() if parsed_date else None,
            "days_from_now": days_from_now,
            "urgency": urgency,
        })

    items.sort(key=lambda x: (x["parsed_date"] is None, x["parsed_date"] or "9999-99-99"))

    return jsonify({"session_id": session_id, "items": items}), 200


@sessions_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    session_obj = Session.query.get(session_id)
    if not session_obj:
        return jsonify({"error": "Session not found"}), 404
    for doc in session_obj.documents:
        if doc.bucket and doc.object_key:
            delete_file(doc.bucket, doc.object_key)
    db.session.delete(session_obj)
    db.session.commit()
    return jsonify({"message": f"Session {session_id} deleted"}), 200
