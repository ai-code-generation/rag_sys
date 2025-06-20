# RAG Playground Service

The RAG Playground is a user-friendly web interface built with Streamlit that provides an interactive way to test and use the RAG system.

## Overview

This service provides:
- Document upload interface for knowledge base management
- Interactive chat interface for querying documents
- Real-time streaming responses from the chain server
- Support for both default and speech-enabled modes

## Architecture

```
src/
├── default/               # Default UI mode
│   ├── __main__.py       # Entry point
│   ├── api.py            # API client for chain server
│   ├── chat_client.py    # Chat interface logic
│   ├── configuration.py  # UI configuration
│   ├── pages/            # Streamlit pages
│   ├── static/           # Static assets
│   └── assets/           # UI assets
└── speech/               # Speech-enabled UI mode
    ├── __main__.py       # Entry point with speech features
    ├── asr_utils.py      # Automatic Speech Recognition
    ├── tts_utils.py      # Text-to-Speech
    └── ...               # Similar structure to default
```

## Features

### Default Mode
- **Knowledge Base Tab**: Upload and manage documents (TXT, PDF, MD)
- **Chat Tab**: Interactive Q&A with uploaded documents
- **Settings**: Configure model parameters and retrieval settings
- **Document Management**: View, search, and delete uploaded documents

### Speech Mode (Optional)
- All default mode features plus:
- Voice input for questions
- Text-to-speech for responses
- NVIDIA Riva integration for speech processing

## Configuration

The service is configured through environment variables:

### Chain Server Connection
- `APP_SERVERURL` - Chain server URL (default: http://chain-server)
- `APP_SERVERPORT` - Chain server port (default: 8081)

### UI Configuration
- `APP_MODELNAME` - Model name displayed in UI
- `PLAYGROUND_MODE` - UI mode (default or speech)

### Observability
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry endpoint
- `ENABLE_TRACING` - Enable/disable tracing

## Usage

### Uploading Documents
1. Navigate to the "Knowledge Base" tab
2. Click "Upload Document" 
3. Select your TXT, PDF, or MD files
4. Wait for processing confirmation

### Asking Questions
1. Go to the "Chat" tab
2. Enable "Use knowledge base" for RAG queries
3. Type your question and press Enter
4. View streaming responses in real-time

### Managing Documents
- View all uploaded documents in the Knowledge Base tab
- Search through document content
- Delete documents you no longer need

## Development

### Building the Service
```bash
# Default mode
docker build -t rag-playground --build-arg PLAYGROUND_MODE=default .

# Speech mode
docker build -t rag-playground --build-arg PLAYGROUND_MODE=speech .
```

### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# For speech mode, also install:
pip install nvidia-riva-client==2.14.0

# Set environment variables
export APP_SERVERURL="http://localhost"
export APP_SERVERPORT="8081"

# Run the playground
python -m src.default  # or src.speech for speech mode
```

### Customizing the UI

The Streamlit interface can be customized by:
1. Modifying pages in `src/default/pages/` or `src/speech/pages/`
2. Updating static assets in `src/default/static/`
3. Changing configuration in `src/default/configuration.py`

## Dependencies

Key dependencies include:
- Streamlit - Web UI framework
- Requests - HTTP client for chain server
- NVIDIA Riva Client - Speech processing (speech mode only)
- Plotly - Data visualization
- Pandas - Data manipulation

## Troubleshooting

### Common Issues

1. **Cannot connect to chain server**
   - Verify `APP_SERVERURL` and `APP_SERVERPORT` are correct
   - Ensure chain server is running and accessible

2. **Document upload fails**
   - Check file format (only TXT, PDF, MD supported)
   - Verify chain server has sufficient resources

3. **Speech features not working**
   - Ensure you're using speech mode build
   - Check NVIDIA Riva service availability
   - Verify microphone permissions in browser
