# 🏠 AI-Based Interior Designer

An AI-powered interior design platform that generates personalized room designs using image segmentation, natural language processing, and AI image generation.

---

## ✨ Features

- 🎨 **AI-Generated Designs** — Create stunning interiors from text descriptions
- 🔍 **Image Segmentation** — Detect walls, furniture, and room structure via YOLOv8
- 💬 **Natural Language Processing** — Understands descriptive design prompts
- 🏠 **Multiple Room Types** — Bedroom, kitchen, bathroom, living room, office, lab, classroom, auditorium, hall
- 🎯 **Directional Color Control** — Specify North/South/East/West wall colors
- 💰 **Cost Estimation** — Budget-friendly suggestions with detailed breakdowns

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Segmentation:** YOLOv8 (`ultralytics`)
- **Image Generation:** OpenAI DALL-E 3 / Stable Diffusion (Hugging Face)
- **NLP:** GPT-4 via OpenAI API

---

## 🚀 Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/your-username/ai-interior-designer.git
cd ai-interior-designer

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download YOLOv8 segmentation model
python -c "from ultralytics import YOLO; YOLO('yolov8n-seg.pt')"

# 5. Create required directories
mkdir uploads outputs static/generated

# 6. Configure environment variables
cp .env.example .env
# Edit .env and add your API keys

# 7. Run the app
python app.py
```

Open in browser 👉 `http://localhost:5000`

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
AZURE_OPENAI_KEY=your_azure_key_here
AZURE_OPENAI_ENDPOINT=your_azure_endpoint_here
HUGGINGFACE_TOKEN=your_huggingface_token_here
FLASK_SECRET_KEY=your_secret_key_here
FLASK_DEBUG=True
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/segment` | Segment uploaded room image |
| `POST` | `/api/analyze-prompt` | Analyze user's design prompt |
| `POST` | `/api/generate-design` | Generate design from prompt |
| `POST` | `/api/redesign-room` | Regenerate design with edits |
| `POST` | `/api/enhance-design` | Enhance an existing design |
| `GET` | `/api/room-types` | Get room types & furniture options |

---

## 🗂️ Project Structure

```
ai-interior-designer/
├── app.py
├── cost_estimator.py
├── requirements.txt
├── .env
├── yolov8n-seg.pt
├── models/
│   └── segmentation.py
├── utils/
│   ├── nlp_processor.py
│   └── image_generator.py
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── generated/
├── uploads/
└── outputs/
```

---

## 💰 API Cost Reference

| Service | Cost |
|---------|------|
| OpenAI DALL-E 3 | ~$0.04–$0.08 per image |
| GPT-4 Analysis | ~$0.01–$0.03 per request |
| Stable Diffusion (local) | Free *(GPU recommended)* |

---

## ⚠️ Troubleshooting

- Ensure `.env` has valid API keys before running
- Use a GPU for faster local Stable Diffusion inference
- If you get `CUDA out of memory`, reduce input image resolution
- To change the port: edit `app.run(port=8000)` in `app.py`

---

## 🌟 Roadmap

- [ ] 3D model generation & VR support
- [ ] Real-time collaborative design
- [ ] Furniture retailer integration
- [ ] Multi-room floor plans
- [ ] Mobile app version

---

## 📜 License

For educational purposes only. Please comply with all API provider terms of service.