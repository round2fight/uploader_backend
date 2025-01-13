import time
from flask import Flask, request, jsonify
from flask_cors import CORS 
import os

app = Flask(__name__)
CORS(app) 
# CORS(app, origins=["http://localhost:3000"])  # Allow only your React app


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

    # username = request.form.get('username')
    # company_name = request.form.get('companyName')

    # if not username or not company_name:
    #     return {"error": "Username and company name are required"}, 400

    # user_info_path = os.path.join(UPLOAD_FOLDER, "user_info.txt")
    # with open(user_info_path, "a") as f:
    #     f.write(f"Username: {username}, Company: {company_name}\n")

    if 'files' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    files = request.files.getlist('files')  # Accept multiple files
    for file in files:
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)

    return jsonify({"message": "Files uploaded successfully!"}), 200

if __name__ == '__main__':
    app.run(debug=True)