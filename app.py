import time
from flask import Flask, request, jsonify
from flask_cors import CORS 
import os

app = Flask(__name__)
CORS(app) 
# CORS(app, origins=["http://localhost:3000","https://meowtest.work.gd"])

# Configure upload folder
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/api/ping', methods=['POST','GET'])
def ping():
    return jsonify({"message": "pong"})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    # Get folder name from request
    new_folder_name = request.form.get('newFolderName')
    if not new_folder_name:
        return jsonify({"error": "Missing folder name"}), 400

    upload_path = os.path.join(UPLOAD_FOLDER, new_folder_name)  
    os.makedirs(upload_path, exist_ok=True)  # Create folder if it doesn't exist

    files = request.files.getlist('files')  # Accept multiple files
    
    for file in files:
        if file:
            relative_path = file.filename  # Preserve original folder structure
            file_path = os.path.join(upload_path, relative_path)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Ensure subfolder exists
            file.save(file_path)  # Save file in correct subfolder

    return jsonify({"message": f"Files uploaded to {new_folder_name} successfully!"}), 200

if __name__ == '__main__':
    app.run(debug=True)