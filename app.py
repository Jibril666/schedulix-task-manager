"""
Schedulix Backend — Flask + MongoDB
Kelompok 17 | Technopreneurship for AI | IPB University
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# ── Koneksi MongoDB ──────────────────────────────────────────────────────────
# Ganti MONGO_URI dengan Atlas URI kamu, atau biarkan pakai localhost
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME   = "schedulix_db"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.server_info()
    db    = client[DB_NAME]
    tasks = db["tasks"]
    print(f"✅  MongoDB terhubung: {MONGO_URI}")
except Exception as e:
    print(f"⚠️   MongoDB tidak tersedia ({e}). Pakai in-memory storage.")
    db    = None
    tasks = None

# ── In-memory fallback ───────────────────────────────────────────────────────
_mem = [
    {"_id":"demo1","name":"Laporan Praktikum Technopreneurship",
     "deadline":"2026-04-29","priority":"high","status":"pending",
     "created_at":datetime.now().isoformat()},
    {"_id":"demo2","name":"Tugas Kalkulus Bab 5",
     "deadline":"2026-05-03","priority":"medium","status":"pending",
     "created_at":datetime.now().isoformat()},
    {"_id":"demo3","name":"Presentasi Kimia Organik",
     "deadline":"2026-05-10","priority":"low","status":"done",
     "created_at":datetime.now().isoformat()},
]

def use_mongo():
    return db is not None and tasks is not None

def serial(doc):
    doc["_id"] = str(doc["_id"])
    return doc

# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "app": "Schedulix API",
        "version": "1.0",
        "storage": "MongoDB" if use_mongo() else "In-Memory",
        "endpoints": {
            "GET  /tasks":          "Ambil semua task",
            "POST /tasks":          "Tambah task baru",
            "PATCH /tasks/<id>":    "Update status task",
            "DELETE /tasks/<id>":   "Hapus task",
        }
    })


@app.route("/tasks", methods=["GET"])
def get_tasks():
    try:
        if use_mongo():
            all_tasks = list(tasks.find().sort("created_at", -1))
            return jsonify([serial(t) for t in all_tasks])
        return jsonify(_mem)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tasks", methods=["POST"])
def add_task():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("deadline"):
        return jsonify({"error": "Field 'name' dan 'deadline' wajib diisi"}), 400

    new_task = {
        "name":       data["name"].strip(),
        "deadline":   data["deadline"],
        "priority":   data.get("priority", "medium"),
        "status":     data.get("status", "pending"),
        "created_at": datetime.now().isoformat(),
    }

    try:
        if use_mongo():
            result = tasks.insert_one(new_task)
            new_task["_id"] = str(result.inserted_id)
        else:
            import uuid
            new_task["_id"] = str(uuid.uuid4())[:8]
            _mem.insert(0, new_task)
        return jsonify(new_task), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tasks/<task_id>", methods=["PATCH"])
def update_task(task_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body kosong"}), 400
    try:
        if use_mongo():
            result = tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"status": data.get("status", "pending")}}
            )
            if result.matched_count == 0:
                return jsonify({"error": "Task tidak ditemukan"}), 404
        else:
            for t in _mem:
                if t["_id"] == task_id:
                    t["status"] = data.get("status", "pending")
                    break
        return jsonify({"message": "Task diperbarui"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    global _mem
    try:
        if use_mongo():
            result = tasks.delete_one({"_id": ObjectId(task_id)})
            if result.deleted_count == 0:
                return jsonify({"error": "Task tidak ditemukan"}), 404
        else:
            _mem = [t for t in _mem if t["_id"] != task_id]
        return jsonify({"message": "Task dihapus"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚀  Schedulix Backend → http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5001)
