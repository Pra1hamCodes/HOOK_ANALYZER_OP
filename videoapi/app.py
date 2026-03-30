from flask import Flask, request, jsonify
from pathlib import Path
import tempfile, os
from ingestion import ingest_video

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'.mp4', '.mov', '.webm'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file in request'}), 400

    file = request.files['file']

    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported format. Use MP4, MOV, or WebM'}), 415

    # Save upload to a temp file so ffmpeg-python can work with it
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = ingest_video(tmp_path)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 422
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.unlink(tmp_path)  # always clean up the upload


if __name__ == '__main__':
    app.run(debug=True)