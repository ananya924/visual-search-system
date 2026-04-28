from fastapi import FastAPI, UploadFile, File
from services.search_service import get_results

# ✅ ADD THIS IMPORT HERE (top with other imports)
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# ✅ ADD THIS RIGHT AFTER app = FastAPI()
app.mount("/images", StaticFiles(directory="../images"), name="images")


@app.get("/")
def home():
    return {"message": "Backend running"}


@app.post("/search")
async def search_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    results = get_results(image_bytes)
    return results