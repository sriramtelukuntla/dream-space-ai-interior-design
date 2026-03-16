# Dream Space: AI-Powered Interior Designer

A comprehensive interior design platform powered by AI that generates personalized design solutions using image segmentation, natural language processing, and AI image generation.

## Features

- 🎨 **AI-Generated Designs**: Create stunning interior designs from text descriptions
- 🔍 **Image Segmentation**: Analyze existing room images to identify walls, furniture, and objects
- 💬 **Natural Language Processing**: Describe your vision naturally - the AI understands
- 🏠 **Multiple Room Types**: Bedroom, kitchen, bathroom, living room, office, lab, classroom, auditorium, hall
- 🎯 **Directional Color Control**: Specify colors for North, South, East, and West walls
- 🪑 **Smart Furniture Placement**: AI suggests appropriate furniture based on room type
- ✨ **Design Enhancement**: Iteratively improve generated designs
- 📥 **Easy Export**: Download your designs in high quality

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- OpenAI API key (for DALL-E image generation)
- OR Hugging Face account (for local Stable Diffusion)

### Step 1: Clone or Download

```bash
# Create project directory
mkdir dream-space
cd dream-space
```

### Step 2: Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### Step 3: Download YOLO Model

The application uses YOLOv8 for segmentation. Download the model:

```bash
# This will download automatically on first run, or manually:
python -c "from ultralytics import YOLO; YOLO('yolov8n-seg.pt')"
```

### Step 4: Configure Environment Variables

Create a `.env` file in the root directory:

```bash
# Copy the template
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# OpenAI API Key (required)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Azure OpenAI
AZURE_OPENAI_KEY=your_azure_key_here
AZURE_OPENAI_ENDPOINT=your_azure_endpoint_here

# Optional: Hugging Face (for local Stable Diffusion)
HUGGINGFACE_TOKEN=your_huggingface_token_here

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
FLASK_DEBUG=True
```

### Step 5: Create Required Directories

```bash
mkdir uploads outputs static/generated
```

### Step 6: Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## Getting API Keys

### OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste into `.env` file

**Note**: DALL-E 3 usage costs approximately $0.04 per image (standard quality) or $0.08 per image (HD quality)

### Hugging Face Token (Optional - for Local Generation)

1. Go to [Hugging Face](https://huggingface.co/)
2. Sign up or log in
3. Go to Settings → Access Tokens
4. Create a new token
5. Accept model licenses for Stable Diffusion models

## Usage Guide

### 1. Basic Usage

1. **Open the application** in your browser: `http://localhost:5000`

2. **Read the instructions** and prompt template on the homepage

3. **Enter your design description** in the text area, for example:
   ```
   Design a modern bedroom with 12ft x 10ft dimensions. 
   North wall should be light blue, south wall white, 
   east wall gray, and west wall cream. Include a queen-size bed, 
   two nightstands, wardrobe, study table with chair, and curtains. 
   Style should be minimalist with natural lighting.
   ```

4. **Click "Generate Design"** and wait for the AI to create your design

5. **Download or enhance** the generated image

### 2. Advanced Usage with Image Upload

1. **Upload an existing room image** by clicking the upload area

2. **Click "Segment Image"** to analyze the room structure

3. **View segmentation results** to see detected objects and colors

4. **Describe modifications** you want in the text area

5. **Generate** to see your redesigned space

### 3. Using the Prompt Template

Copy the example prompt and customize:

- **Room Type**: bedroom, kitchen, living room, etc.
- **Dimensions**: Specify in feet or meters
- **Wall Colors**: Use North, South, East, West directions
- **Furniture**: List specific items you want
- **Style**: modern, traditional, minimalist, rustic, etc.
- **Lighting**: Natural, warm, bright, dim, etc.

### 4. Room-Specific Furniture Suggestions

The AI automatically suggests appropriate furniture based on room type:

- **Bedroom**: bed, nightstand, wardrobe, dresser, study table
- **Kitchen**: cabinets, countertops, stove, refrigerator, sink, dining table
- **Bathroom**: sink, toilet, shower, bathtub, mirror, cabinet
- **Living Room**: sofa, coffee table, TV stand, bookshelf, lamp
- **Office**: desk, office chair, bookshelf, filing cabinet
- **Lab**: lab tables, stools, cabinets, equipment racks
- **Classroom**: desks, chairs, whiteboard, projector
- **Auditorium**: seats, stage, podium, sound system
- **Hall**: seating area, console table, mirror, decorations

## API Endpoints

### POST `/api/segment`
Segment uploaded room image
- **Input**: multipart/form-data with 'image' file
- **Output**: Segmentation results with masks and detected objects

### POST `/api/analyze-prompt`
Analyze user's design prompt
- **Input**: `{"prompt": "...", "room_type": "..."}`
- **Output**: Structured design requirements

### POST `/api/generate-design`
Generate interior design from prompt
- **Input**: `{"prompt": "...", "room_type": "..."}`
- **Output**: Generated design image

### POST `/api/redesign-room`
Redesign specific parts of an uploaded room
- **Input**: multipart/form-data with 'image', 'mask', 'prompt'
- **Output**: Redesigned image

### POST `/api/enhance-design`
Enhance existing design
- **Input**: `{"image_base64": "...", "enhancements": "..."}`
- **Output**: Enhanced image

### GET `/api/room-types`
Get available room types and furniture options

## Troubleshooting

### "Missing required environment variables" Error

Make sure your `.env` file contains valid API keys:
```bash
cat .env  # Check if file exists and has content
```

### "CUDA out of memory" Error (Local Stable Diffusion)

If using local generation and getting memory errors:
1. Set `use_local=False` in `app.py` to use OpenAI instead
2. OR reduce image dimensions in generation functions
3. OR use CPU instead of GPU (slower but works)

### "Module not found" Errors

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt --upgrade
```

### Slow Generation Times

- **OpenAI DALL-E**: Usually 10-30 seconds
- **Local Stable Diffusion**: 1-5 minutes depending on hardware
- For faster results, use OpenAI API (requires API key and costs)

### Port Already in Use

If port 5000 is already in use:
```bash
# Use a different port
python app.py --port 8000
```

Or modify `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)  # Change port here
```

## Project Structure

```
dream-space/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── .env                       # Environment variables (create this)
├── README.md                  # This file
│
├── models/
│   └── segmentation.py        # Image segmentation module
│
├── utils/
│   ├── nlp_processor.py       # NLP and prompt analysis
│   └── image_generator.py     # AI image generation
│
├── templates/
│   └── index.html             # Main web interface
│
├── static/
│   ├── css/
│   │   └── style.css          # Styling
│   ├── js/
│   │   └── main.js            # Frontend logic
│   └── generated/             # Generated images (auto-created)
│
├── uploads/                   # Uploaded images (auto-created)
└── outputs/                   # Additional outputs (auto-created)
```

## Performance Tips

1. **Use GPU**: If you have an NVIDIA GPU, ensure CUDA is installed for faster local generation
2. **Optimize Prompts**: More specific prompts = better results
3. **Batch Processing**: Generate multiple variations and choose the best
4. **Cache Results**: Save generated designs locally to avoid regenerating

## Cost Considerations

### Using OpenAI (Recommended for Best Quality)

- **DALL-E 3**: ~$0.04-0.08 per image
- **GPT-4**: ~$0.01-0.03 per analysis
- **Typical Cost**: $0.10-0.15 per complete design

### Using Local Stable Diffusion (Free but Slower)

- No API costs
- Requires good hardware (GPU recommended)
- Takes 1-5 minutes per image

## Limitations

1. Generated images are AI-created and may have imperfections
2. Directional wall colors are interpreted by AI (not pixel-perfect)
3. Furniture placement is suggestive, not architectural-grade
4. Dimensions are approximate in generated images
5. API rate limits may apply (check OpenAI documentation)

## Future Enhancements

- [ ] 3D model generation and viewing
- [ ] Virtual reality (VR) support
- [ ] Real-time collaborative design
- [ ] Integration with furniture retailers
- [ ] Cost estimation for implementation
- [ ] Mobile app version
- [ ] Multi-room floor plans

## Credits

- YOLOv8 by Ultralytics for object detection
- OpenAI for GPT and DALL-E APIs
- LangChain for NLP pipeline
- Stable Diffusion for local image generation

## License

This project is for educational purposes. Ensure compliance with API provider terms of service.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review API provider documentation
3. Ensure all environment variables are set correctly
4. Verify Python version compatibility (3.8+)

## Version

**Version 1.0.0** - Initial Release
- Image segmentation
- NLP-powered prompt analysis
- AI design generation
- Multi-room support
- Directional color specification