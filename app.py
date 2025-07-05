import os
import shutil
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import safe_join

app = Flask(__name__)
CORS(app, origins=["https://udaydigital.shop:8085"])

SSD_UPLOAD_FOLDER = "./uploads/ssd_temp"
HDD_STORAGE_FOLDER = "/mnt/uploads/data"

os.makedirs(SSD_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(HDD_STORAGE_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024 * 1024  # 10GB

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_chunk_folder(new_folder_name: str, relative_path: str) -> str:
    # Use safe_join to avoid path traversal attacks
    return safe_join(SSD_UPLOAD_FOLDER, new_folder_name, relative_path)


def get_final_file_path(new_folder_name: str, relative_path: str, filename: str) -> str:
    return safe_join(HDD_STORAGE_FOLDER, new_folder_name, relative_path, filename)


def read_metadata(meta_file_path: str) -> set:
    if not os.path.exists(meta_file_path):
        return set()
    with open(meta_file_path, "r") as f:
        try:
            data = json.load(f)
            return set(data.get("received_chunks", []))
        except Exception:
            logging.warning(f"Metadata file corrupted: {meta_file_path}")
            return set()


def write_metadata(meta_file_path: str, received_chunks: set):
    temp_meta_path = meta_file_path + ".tmp"
    with open(temp_meta_path, "w") as f:
        json.dump({"received_chunks": sorted(list(received_chunks))}, f)
    os.replace(temp_meta_path, meta_file_path)  # atomic replace


def merge_chunks(chunk_folder: str, filename: str, total_chunks: int, final_path: str):
    os.makedirs(os.path.dirname(final_path), exist_ok=True)

    with open(final_path, "wb") as final_file:
        for i in range(total_chunks):
            part_path = os.path.join(chunk_folder, f"{filename}.part{i}")
            if not os.path.exists(part_path):
                raise FileNotFoundError(f"Missing chunk {i} at {part_path}")

            with open(part_path, "rb") as part_file:
                shutil.copyfileobj(part_file, final_file)

    logging.info(f"✅ Merged file saved: {final_path}")


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large"}), 413


@app.route("/api/ping", methods=["GET", "POST"])
def ping():
    return jsonify({"message": "pong"})


@app.route("/api/upload", methods=["POST"])
def upload_chunk():
    try:
        if "chunk" not in request.files:
            return jsonify({"error": "No chunk file provided"}), 400

        chunk = request.files["chunk"]
        filename = request.form.get("filename")
        relative_path = request.form.get("relativePath")
        chunk_index = request.form.get("chunkIndex")
        total_chunks = request.form.get("totalChunks")
        new_folder_name = request.form.get("newFolderName")

        # Validate required form data
        if not all([filename, relative_path, chunk_index, total_chunks, new_folder_name]):
            return jsonify({"error": "Missing required form data"}), 400

        try:
            chunk_index = int(chunk_index)
            total_chunks = int(total_chunks)
            if chunk_index < 0 or chunk_index >= total_chunks:
                return jsonify({"error": "Invalid chunk index"}), 400
        except ValueError:
            return jsonify({"error": "Chunk index and total chunks must be integers"}), 400

        chunk_folder = get_chunk_folder(new_folder_name, relative_path)
        os.makedirs(chunk_folder, exist_ok=True)

        chunk_path = os.path.join(chunk_folder, f"{filename}.part{chunk_index}")
        chunk.save(chunk_path)

        meta_file = os.path.join(chunk_folder, "chunks.meta")
        received_chunks = read_metadata(meta_file)
        received_chunks.add(chunk_index)
        write_metadata(meta_file, received_chunks)

        logging.info(f"✅ Chunk {chunk_index + 1}/{total_chunks} saved: {chunk_path}")

        # If all chunks received, merge and clean up
        if len(received_chunks) == total_chunks:
            final_file_path = get_final_file_path(new_folder_name, relative_path, filename)
            merge_chunks(chunk_folder, filename, total_chunks, final_file_path)

            # Cleanup chunks and metadata
            shutil.rmtree(chunk_folder)
            logging.info(f"✅ Cleaned up chunk folder: {chunk_folder}")

        return jsonify({"message": f"Chunk {chunk_index + 1}/{total_chunks} received"}), 200

    except Exception as e:
        logging.error(f"❌ Error processing chunk: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
