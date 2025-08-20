import os
import base64
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
load_dotenv()


app = FastAPI()

# Allow CORS (so frontend can call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated images from /static
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load API keys from env
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

@app.post("/generate-tshirt")
async def generate_tshirt(request: Request):
    body = await request.json()
    idea = body.get("idea")

    # --- Step 1: Refine prompt using Gemini ---
    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {"parts": [{"text": f"Turn this idea into a detailed t-shirt design prompt: {idea}"}]}
        ]
    }

    gemini_res = requests.post(gemini_url, json=payload)
    if gemini_res.status_code != 200:
        return {"error": "Gemini API failed", "details": gemini_res.text}

    try:
        refined_prompt = gemini_res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return {"error": "Gemini response parsing failed", "details": gemini_res.json()}

    # --- Step 2: Generate image with Stability AI ---
    stability_url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "application/json",
    }
    files = {
        "prompt": (None, refined_prompt),
        "output_format": (None, "png"),
    }

    image_res = requests.post(stability_url, headers=headers, files=files)
    if image_res.status_code != 200:
        return {"error": "Image generation failed", "details": image_res.text}

    result = image_res.json()
    image_base64 = result.get("image")
    if not image_base64:
        return {"error": "No image data returned", "details": result}

    # Save image locally
    image_bytes = base64.b64decode(image_base64)
    file_name = f"static/tshirt_{hash(idea)}.png"
    with open(file_name, "wb") as f:
        f.write(image_bytes)

    return {
        "prompt": refined_prompt,
        "image_url": f"http://localhost:8000/{file_name}"
    }
