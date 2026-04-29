import os
import io
import numpy as np
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
import torch
import torchvision.models as models
import torchvision.transforms as transforms

# Load ResNet model
model = models.resnet50(pretrained=True)
model = torch.nn.Sequential(*list(model.children())[:-1])
model.eval()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

# Extract features from image bytes
def extract_features(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = transform(image).unsqueeze(0)
    with torch.no_grad():
        features = model(image)
    return features.numpy().flatten()

# Load dataset
DATASET_PATH = os.path.join(os.path.dirname(__file__), "../../images")
image_features = []
image_paths = []

def load_dataset():
    for img_name in os.listdir(DATASET_PATH):
        if img_name.lower().endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(DATASET_PATH, img_name)
            with open(path, "rb") as f:
                vec = extract_features(f.read())
                image_features.append(vec)
                image_paths.append(img_name)

load_dataset()

# MAIN FUNCTION
def get_results(image_bytes):
    query_vec = extract_features(image_bytes)
    sims = cosine_similarity([query_vec], image_features)[0]
    results = sorted(
        zip(image_paths, sims),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    return [
        {
            "image": f"http://127.0.0.1:8000/images/{img}",
            "score": float(score)
        }
        for img, score in results
    ]