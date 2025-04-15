import os
import shutil
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Paths for SSD (temporary storage) and HDD (final storage)
SSD_UPLOAD_FOLDER = "./uploads/ssd_temp"  # Fast temporary storage
HDD_STORAGE_FOLDER = "./mnt/uploads/data"   # Final HDD storage location

# Ensure directories exist
os.makedirs(SSD_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(HDD_STORAGE_FOLDER, exist_ok=True)

# Increase the max request size (10GB)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024 * 1024  # 10GB

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


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
        relative_path = request.form.get("relativePath")  # Keep original folder structure
        chunk_index = request.form.get("chunkIndex")
        total_chunks = request.form.get("totalChunks")
        new_folder_name = request.form.get("newFolderName")

        # Validate required form data
        if not all([filename, relative_path, chunk_index, total_chunks, new_folder_name]):
            return jsonify({"error": "Missing required form data"}), 400

        chunk_index = int(chunk_index)
        total_chunks = int(total_chunks)

        # ✅ Keep folder structure in SSD
        chunk_folder = os.path.join(SSD_UPLOAD_FOLDER, new_folder_name, relative_path)
        os.makedirs(chunk_folder, exist_ok=True)

        # ✅ Save chunk separately
        chunk_path = os.path.join(chunk_folder, f"{filename}.part{chunk_index}")
        chunk.save(chunk_path)

        # ✅ Track received chunks in a metadata file
        meta_file = os.path.join(chunk_folder, "chunks.meta")
        with open(meta_file, "a") as meta:
            meta.write(f"{chunk_index}\n")

        logging.info(f"✅ Chunk {chunk_index + 1}/{total_chunks} saved: {chunk_path}")

        # ✅ Check if all chunks are received
        with open(meta_file, "r") as meta:
            received_chunks = {int(line.strip()) for line in meta.readlines()}

        if len(received_chunks) == total_chunks:
            # ✅ Ensure folder structure in HDD
            final_hdd_path = os.path.join(HDD_STORAGE_FOLDER, new_folder_name, relative_path)
            os.makedirs(os.path.dirname(final_hdd_path), exist_ok=True)

            # ✅ Merge chunks in order
            with open(final_hdd_path, "wb") as final_file:
                for i in range(total_chunks):
                    part_path = os.path.join(chunk_folder, f"{filename}.part{i}")

                    if not os.path.exists(part_path):
                        logging.error(f"❌ Missing chunk: {part_path}")
                        return jsonify({"error": f"Missing chunk {i}"}), 500

                    with open(part_path, "rb") as part_file:
                        final_file.write(part_file.read())

            logging.info(f"✅ Merged file saved: {final_hdd_path}")

            # ✅ Cleanup chunk files after merging
            shutil.rmtree(chunk_folder)

        return jsonify({"message": f"Chunk {chunk_index + 1}/{total_chunks} received"}), 200

    except Exception as e:
        logging.error(f"❌ Error processing chunk: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
