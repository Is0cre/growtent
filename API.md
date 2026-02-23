# External Server API Documentation

This document describes the API endpoints that your external server should implement to receive data from the Grow Tent Automation System.

## Authentication

The system supports multiple authentication methods:

### API Key Authentication
```
Header: X-API-Key: your_api_key
```

### Bearer Token Authentication
```
Header: Authorization: Bearer your_token
```

### Basic Authentication
```
Header: Authorization: Basic base64(username:password)
```

---

## Required Endpoints

### 1. Photo Upload

**Endpoint:** `POST /photos/upload`

**Content-Type:** `multipart/form-data`

**Request:**
```
photo: [binary file]
project_id: string
photo_type: string ("latest" | "timelapse" | "diary")
timestamp: ISO 8601 datetime
filename: string
```

**Response:**
```json
{
  "success": true,
  "message": "Photo uploaded successfully",
  "url": "https://global.discourse-cdn.com/netlify/original/3X/2/4/24a7a54d41e362e35fc19b48018bed4b5e6b3d5e.jpeg"
}
```

---

### 2. Sensor Data

**Endpoint:** `POST /sensor-data`

**Content-Type:** `application/json`

**Request:**
```json
{
  "project_id": 1,
  "timestamp": "2024-01-15T12:30:00Z",
  "temperature": 24.5,
  "humidity": 65.2,
  "pressure": 1013.25,
  "gas_resistance": 50000
}
```

**Response:**
```json
{
  "success": true,
  "message": "Sensor data received"
}
```

---

### 3. Project Information

**Endpoint:** `POST /projects`

**Content-Type:** `application/json`

**Request:**
```json
{
  "id": 1,
  "name": "Cannabis Grow 2024",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": null,
  "status": "active",
  "notes": "First hydroponic grow",
  "timestamp": "2024-01-15T12:30:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Project info received"
}
```

---

### 4. Analysis Reports

**Endpoint:** `POST /reports`

**Content-Type:** `application/json`

**Request:**
```json
{
  "id": 1,
  "project_id": 1,
  "timestamp": "2024-01-15T12:00:00Z",
  "analysis_text": "Full AI analysis text...",
  "health_score": 8,
  "recommendations": "Continue current feeding schedule...",
  "photo_url": "data/photos/analysis_20240115_120000.jpg",
  "sync_timestamp": "2024-01-15T12:30:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Analysis report received"
}
```

---

## Error Responses

All endpoints should return appropriate error responses:

**400 Bad Request:**
```json
{
  "success": false,
  "error": "Invalid request data"
}
```

**401 Unauthorized:**
```json
{
  "success": false,
  "error": "Invalid authentication credentials"
}
```

**500 Server Error:**
```json
{
  "success": false,
  "error": "Internal server error"
}
```

---

## Connection Testing

The system will test connection to your server by making a GET request to the base URL:

**Endpoint:** `GET /` (or base URL)

**Expected Response:** Any 2xx status code indicates successful connection.

---

## Example Server Implementation (Python Flask)

```python
from flask import Flask, request, jsonify
import os

app = Flask(__name__)
API_KEY = os.environ.get('API_KEY', 'your-secret-key')

def check_auth():
    api_key = request.headers.get('X-API-Key')
    return api_key == API_KEY

@app.route('/')
def index():
    return jsonify({"status": "ok"})

@app.route('/photos/upload', methods=['POST'])
def upload_photo():
    if not check_auth():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    photo = request.files.get('photo')
    project_id = request.form.get('project_id')
    photo_type = request.form.get('photo_type')
    
    if photo:
        filename = photo.filename
        photo.save(f'uploads/{filename}')
        return jsonify({
            "success": True,
            "message": "Photo uploaded",
            "url": f"/uploads/{filename}"
        })
    
    return jsonify({"success": False, "error": "No photo provided"}), 400

@app.route('/sensor-data', methods=['POST'])
def sensor_data():
    if not check_auth():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    data = request.json
    # Store in database...
    print(f"Received sensor data: {data}")
    
    return jsonify({"success": True, "message": "Data received"})

@app.route('/projects', methods=['POST'])
def projects():
    if not check_auth():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    data = request.json
    # Store in database...
    print(f"Received project info: {data}")
    
    return jsonify({"success": True, "message": "Project info received"})

@app.route('/reports', methods=['POST'])
def reports():
    if not check_auth():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    data = request.json
    # Store in database...
    print(f"Received analysis report: {data}")
    
    return jsonify({"success": True, "message": "Report received"})

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(host='0.0.0.0', port=5000)
```

---

## Retry Logic

The Grow Tent system implements retry logic for failed requests:

- **Retry attempts:** Configurable (default: 3)
- **Retry delay:** Configurable (default: 30 seconds)
- **Exponential backoff:** Yes
- **Retry on status codes:** 429, 500, 502, 503, 504

---

## Sync Modes

### Automatic Sync
When enabled, data is synced periodically based on `sync_interval` setting.

### Manual Sync
Users can trigger immediate sync via:
- Web UI: "Sync Now" button
- API: `POST /api/sync/now`
- Telegram: `/sync` command

---

## Webhook Support (Future)

Future versions may support webhooks for real-time updates. Your server can register a webhook URL to receive instant notifications for:
- New photos
- Alert conditions
- Project status changes
- Analysis completions
