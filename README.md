# StormBuster Backend API

FastAPI backend for storm damage analysis and lead generation.

## Setup

1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_API_KEY=your_google_key_here
```

3. Run the server:
```bash
python app.py
```

Or with uvicorn directly:
```bash
uvicorn app:app --reload
```

The API will be available at: http://localhost:8000

## API Documentation

Once running, visit:
- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Endpoints

### Health & Info
- `GET /` - Root endpoint with API info
- `GET /health` - Health check

### AI Models
- `GET /models?tier=basic` - Get available models for subscription tier

### Chat
- `POST /chat` - Send chat message
- `GET /chat-history?limit=50` - Get chat history
- `DELETE /chat-history` - Clear chat history
- `GET /export-chat` - Export chat as JSON

### Analysis
- `POST /analyze-storm` - Analyze storm data
- `POST /generate-lead-insights` - Generate lead insights

### Usage
- `GET /usage-stats?tier=basic` - Get usage statistics

## Example Usage

### Send a Chat Message
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze this storm data",
    "model_id": "gpt-4",
    "subscription_tier": "professional"
  }'
```

### Analyze Storm Data
```bash
curl -X POST "http://localhost:8000/analyze-storm" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-01-15",
    "location": "Dallas, TX",
    "hail_size": "2.5 inches",
    "property_count": 150,
    "avg_property_value": "$350,000"
  }'
```

## Deployment

For production deployment, use:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

Or deploy to cloud platforms like:
- Railway
- Render
- Fly.io
- AWS Lambda
- Google Cloud Run

