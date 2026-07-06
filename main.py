from fastapi import FastAPI, HTTPException, Cookie, Response, Depends, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import json
import os
import time
import uuid
import shutil

app = FastAPI(title="AL-CLINICA API")

PORT = 3000
DATA_FILE = 'data.json'
UPLOAD_DIR = 'uploads'

# Ensure uploads directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory active session store
active_sessions = set()

# Pydantic Schemas
class ClinicSettings(BaseModel):
    clinicName: str
    address: str
    phone: str
    wa: str

class Doctor(BaseModel):
    id: Optional[str] = None
    name: str
    spec: str
    qual: str
    exp: str
    days: str
    time: str
    phone: str
    wa: str
    available: bool
    nextAvail: Optional[str] = None
    avatarBg: Optional[str] = None
    image: Optional[str] = None

class LoginPayload(BaseModel):
    username: str
    password: str

# Helpers to read/write JSON
def read_data():
    if not os.path.exists(DATA_FILE):
        initial = {
            "settings": {
                "clinicName": "AL-CLINICA",
                "address": "123 Healthcare Ave — Open Mon–Sat, 8 AM to 8 PM",
                "phone": "",
                "wa": "917592072319"
            },
            "doctors": []
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial, f, indent=2, ensure_ascii=False)
        return initial
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def verify_admin(session_id: Optional[str] = Cookie(None)):
    if not session_id or session_id not in active_sessions:
        raise HTTPException(status_code=401, detail="Unauthorized. Admin login required.")
    return True

# API endpoints
@app.get("/api/data")
async def get_data(session_id: Optional[str] = Cookie(None)):
    data = read_data()
    is_admin = session_id in active_sessions if session_id else False
    return {
        "isAdmin": is_admin,
        "settings": data.get("settings", {}),
        "doctors": data.get("doctors", [])
    }

@app.post("/api/login")
async def login(payload: LoginPayload, response: Response):
    if payload.username == 'admin' and payload.password == 'admin123':
        session_id = str(uuid.uuid4())
        active_sessions.add(session_id)
        response.set_cookie(key="session_id", value=session_id, httponly=True, path="/")
        return {"success": True}
    raise HTTPException(status_code=401, detail="Invalid username or password.")

@app.post("/api/logout")
async def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    if session_id in active_sessions:
        active_sessions.remove(session_id)
    response.delete_cookie(key="session_id", path="/")
    return {"success": True}

@app.post("/api/settings")
async def update_settings(settings: ClinicSettings, authorized: bool = Depends(verify_admin)):
    data = read_data()
    data["settings"] = settings.dict()
    write_data(data)
    return {"success": True, "settings": data["settings"]}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), authorized: bool = Depends(verify_admin)):
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"doc_{uuid.uuid4().hex}{file_ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"/uploads/{filename}"}

@app.post("/api/doctors")
async def update_doctor(doc: Doctor, authorized: bool = Depends(verify_admin)):
    data = read_data()
    doctors = data.get("doctors", [])
    
    if doc.id:
        # Edit existing doctor
        idx = next((i for i, d in enumerate(doctors) if d['id'] == doc.id), -1)
        if idx == -1:
            raise HTTPException(status_code=404, detail="Doctor not found.")
        
        avatar_bg = doctors[idx].get("avatarBg")
        doctors[idx] = {
            "id": doc.id,
            "name": doc.name,
            "spec": doc.spec,
            "qual": doc.qual,
            "exp": doc.exp,
            "days": doc.days,
            "time": doc.time,
            "phone": doc.phone,
            "wa": doc.wa,
            "available": doc.available,
            "nextAvail": "" if doc.available else (doc.nextAvail or "Next: Tomorrow"),
            "avatarBg": avatar_bg,
            "image": doc.image
        }
        updated_doc = doctors[idx]
    else:
        # Create new doctor
        def get_avatar_bg(name_str):
            gradients = [
                "linear-gradient(135deg, var(--primary), var(--cyan))",
                "linear-gradient(135deg, #10b981, #06b6d4)",
                "linear-gradient(135deg, #f59e0b, #ef4444)",
                "linear-gradient(135deg, #8b5cf6, #6366f1)",
                "linear-gradient(135deg, #ec4899, #f43f5e)",
                "linear-gradient(135deg, #0ea5e9, #38bdf8)"
            ]
            char_sum = sum(ord(c) for c in name_str)
            return gradients[char_sum % len(gradients)]

        updated_doc = {
            "id": "doc-" + str(int(time.time() * 1000)),
            "name": doc.name,
            "spec": doc.spec,
            "qual": doc.qual,
            "exp": doc.exp,
            "days": doc.days,
            "time": doc.time,
            "phone": doc.phone,
            "wa": doc.wa,
            "available": doc.available,
            "nextAvail": "" if doc.available else (doc.nextAvail or "Next: Tomorrow"),
            "avatarBg": get_avatar_bg(doc.name),
            "image": doc.image
        }
        doctors.append(updated_doc)
        
    data["doctors"] = doctors
    write_data(data)
    return {"success": True, "doctors": doctors}

@app.delete("/api/doctors/{doctor_id}")
async def delete_doctor(doctor_id: str, authorized: bool = Depends(verify_admin)):
    data = read_data()
    doctors = data.get("doctors", [])
    doctors = [d for d in doctors if d["id"] != doctor_id]
    data["doctors"] = doctors
    write_data(data)
    return {"success": True, "doctors": doctors}

# Mount uploads directory statically
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Serve main webpage at root
@app.get("/")
async def read_root():
    return FileResponse('index.html')

# Catch-all to serve static files in the directory, falling back to index.html
@app.get("/{catchall:path}")
async def catch_all(catchall: str):
    if not catchall.startswith("api/"):
        file_path = catchall.lstrip("/")
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse('index.html')
    raise HTTPException(status_code=404, detail="API endpoint not found")
