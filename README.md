# AI Video Enhancer

Production-ready web application for AI-powered video enhancement, featuring:
- **Real-ESRGAN** for AI upscaling (2x/4x)
- **RIFE** for frame interpolation (60/120 FPS)
- **Live wallpaper optimization** with seamless looping

## Features

- 🎬 **AI Upscaling**: Real-ESRGAN neural network for superior quality
- 🎞️ **Frame Interpolation**: RIFE optical flow for smooth motion
- 📺 **Resolution Presets**: 1080p, 1440p, 4K output options
- ⚡ **GPU Acceleration**: CUDA support for fast processing
- 🔄 **Loop Optimization**: Seamless looping for live wallpapers
- 🎨 **Dark Neon UI**: Modern React interface with Tailwind CSS

## Tech Stack

### Frontend
- React 18 + Vite
- Tailwind CSS (dark neon theme)
- Drag & drop upload
- Real-time progress tracking

### Backend
- Python FastAPI
- FFmpeg for video processing
- Real-ESRGAN for upscaling
- RIFE for interpolation
- Async background tasks
- GPU acceleration (CUDA)

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- FFmpeg
- (Optional) NVIDIA GPU with CUDA

### Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/your-repo/ai-video-enhancer.git
   cd ai-video-enhancer
   ```

2. **Setup Backend:**
   ```bash
   cd server
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # For GPU support, install PyTorch with CUDA:
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

3. **Setup Frontend:**
   ```bash
   cd client
   npm install
   ```

4. **Start Development Servers:**

   Backend (Terminal 1):
   ```bash
   cd server
   source venv/bin/activate
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

   Frontend (Terminal 2):
   ```bash
   cd client
   npm run dev
   ```

5. **Open:** http://localhost:3000

## Docker Deployment

### Production

```bash
cd docker
docker-compose up -d --build
```

Access at http://localhost

### Development with GPU

```bash
cd docker
docker-compose -f docker-compose.dev.yml up --build
```

### GPU Support

Ensure NVIDIA Container Toolkit is installed:
```bash
# Ubuntu/Debian
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

Uncomment GPU section in `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/upload` | POST | Upload video |
| `/enhance` | POST | Start enhancement job |
| `/status/{job_id}` | GET | Get job status |
| `/download/{job_id}` | GET | Download result |

### Enhancement Parameters

| Parameter | Type | Options | Description |
|-----------|------|---------|-------------|
| `resolution` | string | original, 1080p, 1440p, 4k | Target resolution |
| `upscale_factor` | int | 2, 4 | AI upscale multiplier |
| `target_fps` | string | original, 60, 120 | Target frame rate |
| `denoise` | bool | true/false | Enable denoising |
| `sharpen` | bool | true/false | Enable sharpening |
| `loop_optimize` | bool | true/false | Optimize for seamless looping |

## Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    Video Processing Pipeline                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. UPLOAD          2. EXTRACT        3. AI UPSCALE             │
│  ┌─────────┐       ┌─────────┐       ┌─────────────┐            │
│  │  Video  │  ──▶  │ Frames  │  ──▶  │ Real-ESRGAN │            │
│  │  File   │       │  (PNG)  │       │   (2x/4x)   │            │
│  └─────────┘       └─────────┘       └─────────────┘            │
│                                            │                     │
│                                            ▼                     │
│  6. OUTPUT         5. REASSEMBLE     4. INTERPOLATE             │
│  ┌─────────┐       ┌─────────┐       ┌─────────────┐            │
│  │ Enhanced│  ◀──  │ H.265   │  ◀──  │    RIFE     │            │
│  │  Video  │       │ Encode  │       │  (60/120)   │            │
│  └─────────┘       └─────────┘       └─────────────┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Bitrate Configuration

| Resolution | Bitrate Range | Default |
|------------|---------------|---------|
| 1080p | 15-20 Mbps | 18M |
| 1440p | 20-30 Mbps | 28M |
| 4K | 30-50 Mbps | 45M |

## File Structure

```
ai-video-enhancer/
├── client/                 # React frontend
│   ├── src/
│   │   ├── App.jsx        # Main application
│   │   ├── api.js         # API service
│   │   └── index.css      # Tailwind styles
│   ├── package.json
│   └── vite.config.js
├── server/                 # Python backend
│   ├── main.py            # FastAPI application
│   ├── config.py          # Configuration
│   ├── processors/
│   │   ├── pipeline.py    # Main processing pipeline
│   │   ├── upscaler.py    # Real-ESRGAN upscaler
│   │   ├── interpolator.py # RIFE interpolator
│   │   ├── ffmpeg_utils.py # FFmpeg utilities
│   │   └── job_manager.py # Job management
│   └── requirements.txt
├── docker/                 # Docker configuration
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── models/                 # AI model storage
└── temp/                   # Temporary files
    ├── uploads/
    ├── outputs/
    └── processing/
```

## Security

- File type validation (mp4, mov, webm, gif only)
- Max upload size: 2GB
- Automatic cleanup of temp files (2 hours)
- Sanitized filenames
- Path traversal prevention

## Performance Tips

1. **GPU Required**: For practical use, NVIDIA GPU with 6GB+ VRAM recommended
2. **Memory**: 16GB+ RAM recommended for 4K processing
3. **Storage**: SSD recommended for temp file operations
4. **Workers**: Adjust `MAX_WORKERS` in config for CPU core count
5. **ESRGAN Warm Cache**: Keep `ESRGAN_KEEP_LOADED=true` to avoid reloading models between jobs
6. **Precision**: Keep `ESRGAN_FP16=true` on CUDA GPUs for faster inference
7. **Tile Tuning**: Leave `ESRGAN_TILE` empty for auto mode, or set manually (`128`, `256`, `400`, or `0` for no tiling on high VRAM)

### ESRGAN Tuning (server/.env)

```env
ESRGAN_FP16=true
ESRGAN_TILE=
ESRGAN_TILE_PAD=10
ESRGAN_KEEP_LOADED=true
ESRGAN_REQUIRE_CUDA=false
```

- `ESRGAN_FP16`: Enables half precision on CUDA (faster, lower VRAM use).
- `ESRGAN_TILE`: Empty = auto hardware-aware tile selection. Set a fixed value to prioritize stability or speed.
- `ESRGAN_TILE_PAD`: Tile overlap padding to reduce seam artifacts.
- `ESRGAN_KEEP_LOADED`: Reuses loaded models across jobs for smoother repeated runs.
- `ESRGAN_REQUIRE_CUDA`: When `true`, Real-ESRGAN jobs fail fast if no CUDA GPU is detected. Keep `false` to allow CPU fallback.

## Troubleshooting

### FFmpeg not found
```bash
# Ubuntu
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
winget install ffmpeg
```

### CUDA not detected
```bash
# Verify CUDA installation
nvidia-smi

# Reinstall PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Out of Memory
- Reduce `upscale_factor` from 4x to 2x
- Process shorter video segments
- Close other GPU applications

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request
