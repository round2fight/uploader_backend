import os
import shutil
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Paths for SSD (temporary storage) and HDD (final storage)
SSD_UPLOAD_FOLDER = "./uploads/ssd_temp"  # Fast temporary storage
HDD_STORAGE_FOLDER = "./uploads/hdd_storage"   # Final HDD storage location

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

# 🔹 Remove empty directories from SSD after moving the file
def remove_empty_dirs(path, root):
    while path != root:  # Don't delete the root SSD folder
        try:
            os.rmdir(path)  # Removes only if empty
            logging.info(f"🗑️ Removed empty folder: {path}")
        except OSError:
            break  # Directory is not empty, stop
        path = os.path.dirname(path)  # Move up one level



@app.route("/api/upload", methods=["POST"])
def upload_chunk():
    try:
        # Validate request
        if "chunk" not in request.files:
            return jsonify({"error": "No chunk file provided"}), 400

        chunk = request.files["chunk"]
        filename = request.form.get("filename")
        relative_path = request.form.get("relativePath")
        chunk_index = request.form.get("chunkIndex")
        total_chunks = request.form.get("totalChunks")
        new_folder_name = request.form.get("newFolderName")

        # Ensure all required form data is present
        if not all([filename, relative_path, chunk_index, total_chunks, new_folder_name]):
            return jsonify({"error": "Missing required form data"}), 400

        # Convert chunk indexes to integers
        chunk_index = int(chunk_index)
        total_chunks = int(total_chunks)

        # Temporary SSD path
        ssd_upload_dir = os.path.join(SSD_UPLOAD_FOLDER, new_folder_name)
        file_path = os.path.join(ssd_upload_dir, relative_path)

        # Ensure SSD directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Append chunks in the correct order
        with open(file_path, "ab") as f:
            f.write(chunk.read())

        logging.info(f"Received chunk {chunk_index + 1}/{total_chunks} for {filename}")

        # If last chunk, move to HDD
        if chunk_index == total_chunks - 1:
            final_hdd_path = os.path.join(HDD_STORAGE_FOLDER, new_folder_name, relative_path)

            # Ensure HDD directory exists
            os.makedirs(os.path.dirname(final_hdd_path), exist_ok=True)

            # Move file to HDD
            shutil.move(file_path, final_hdd_path)
            logging.info(f"✅ File {filename} moved to HDD: {final_hdd_path}")

            # Call function to remove empty folders
            # remove_empty_dirs(os.path.dirname(file_path), SSD_UPLOAD_FOLDER)

        return jsonify({"message": f"Chunk {chunk_index + 1}/{total_chunks} received"}), 200

    except Exception as e:
        logging.error(f"❌ Error processing chunk: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
