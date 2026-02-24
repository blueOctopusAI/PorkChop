"""Phase 3: Flask web frontend — browsable, searchable, shareable bill analysis."""

import json
from pathlib import Path

from flask import Flask, render_template, request, jsonify, abort

from ..database import Database


def create_app(db_path=None):
    app = Flask(__name__)
    db = Database(Path(db_path) if db_path else None)

    @app.context_processor
    def inject_stats():
        return {"db_stats": db.get_stats()}

    # --- Pages ---

    @app.route("/")
    def index():
        bills = db.list_bills(limit=50)
        stats = db.get_stats()
        return render_template("index.html", bills=bills, stats=stats)

    @app.route("/bill/<int:bill_id>")
    def bill_detail(bill_id):
        bill = db.get_bill(bill_id)
        if not bill:
            abort(404)
        versions = db.get_versions(bill_id)
        sections = db.get_sections(bill_id)
        spending = db.get_spending(bill_id)
        total_spending = db.get_total_spending(bill_id)
        refs = db.get_references(bill_id)
        deadlines = db.get_deadlines(bill_id)
        entities = db.get_entities(bill_id)
        summary = db.get_bill_summary(bill_id)
        pork = db.get_bill_pork_summary(bill_id)
        return render_template(
            "bill.html",
            bill=bill,
            versions=versions,
            sections=sections,
            spending=spending,
            total_spending=total_spending,
            refs=refs,
            deadlines=deadlines,
            entities=entities,
            summary=summary,
            pork=pork,
        )

    @app.route("/bill/<int:bill_id>/spending")
    def bill_spending(bill_id):
        bill = db.get_bill(bill_id)
        if not bill:
            abort(404)
        spending = db.get_spending(bill_id)
        total = db.get_total_spending(bill_id)
        pork_scores = db.get_pork_scores(bill_id)
        pork_map = {s["spending_item_id"]: s for s in pork_scores}
        return render_template(
            "spending.html",
            bill=bill,
            spending=spending,
            total=total,
            pork_map=pork_map,
        )

    @app.route("/bill/<int:bill_id>/compare")
    def bill_compare(bill_id):
        bill = db.get_bill(bill_id)
        if not bill:
            abort(404)
        versions = db.get_versions(bill_id)
        from_id = request.args.get("from", type=int)
        to_id = request.args.get("to", type=int)
        comparison = None
        if from_id and to_id:
            comparison = db.get_comparison(bill_id, from_id, to_id)
            if comparison and comparison.get("changes_json"):
                comparison["changes"] = json.loads(comparison["changes_json"])
            if comparison and comparison.get("spending_diff_json"):
                comparison["spending_diff"] = json.loads(comparison["spending_diff_json"])
        return render_template(
            "compare.html",
            bill=bill,
            versions=versions,
            comparison=comparison,
            from_id=from_id,
            to_id=to_id,
        )

    @app.route("/search")
    def search_page():
        query = request.args.get("q", "")
        results = db.search_bills(query) if query else []
        return render_template("search.html", query=query, results=results)

    # --- API Endpoints ---

    @app.route("/api/bills")
    def api_bills():
        bills = db.list_bills()
        return jsonify(bills)

    @app.route("/api/bills/<int:bill_id>")
    def api_bill(bill_id):
        bill = db.get_bill(bill_id)
        if not bill:
            return jsonify({"error": "not found"}), 404
        bill["spending"] = db.get_spending(bill_id)
        bill["total_spending"] = db.get_total_spending(bill_id)
        bill["deadlines"] = db.get_deadlines(bill_id)
        bill["entities"] = db.get_entities(bill_id)
        bill["summary"] = db.get_bill_summary(bill_id)
        bill["pork"] = db.get_bill_pork_summary(bill_id)
        return jsonify(bill)

    @app.route("/api/bills/<int:bill_id>/spending")
    def api_spending(bill_id):
        spending = db.get_spending(bill_id)
        return jsonify({"spending": spending, "total": db.get_total_spending(bill_id)})

    @app.route("/api/bills/<int:bill_id>/pork")
    def api_pork(bill_id):
        scores = db.get_pork_scores(bill_id)
        summary = db.get_bill_pork_summary(bill_id)
        return jsonify({"scores": scores, "summary": summary})

    @app.route("/api/search")
    def api_search():
        query = request.args.get("q", "")
        if not query:
            return jsonify({"error": "query required"}), 400
        return jsonify(db.search_bills(query))

    @app.route("/api/stats")
    def api_stats():
        return jsonify(db.get_stats())

    # --- Error Handlers ---

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "not found"}), 404
        return render_template("base.html", error="Page not found"), 404

    return app
