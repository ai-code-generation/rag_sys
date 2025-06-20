# Docker Compose Configuration Fixes

## Issues Fixed

### 1. Missing Environment Variables
**Problem**: The following environment variables were not set, causing warnings:
- `MODEL_DIRECTORY` 
- `NGC_API_KEY`
- `USERID`

**Solution**: 
- Updated `.env.example` with proper default values and documentation
- Created `.env` file with local NIM configuration
- Added default values in docker-compose files using `${VAR:-default}` syntax

### 2. Invalid Volume Specification
**Problem**: When `MODEL_DIRECTORY` was empty, it created invalid volume mount `:/opt/nim/.cache`

**Solution**: 
- Added default values: `${MODEL_DIRECTORY:-./models}:/opt/nim/.cache`
- Created `./models` directory for model caching
- Updated all NIM services with proper defaults

### 3. Configuration for Local vs Cloud Deployment
**Problem**: System was hardcoded for cloud endpoints only

**Solution**:
- Updated `.env` configuration to support both deployment modes
- Created separate deployment scripts:
  - `deploy-local-nim.sh` (Linux/macOS)
  - `deploy-local-nim.bat` (Windows)
- Added configuration helper script: `configure.sh`

## Files Modified

### 1. `.env.example`
- Added NIM-specific environment variables
- Added model engine configuration options
- Added GPU configuration settings

### 2. `.env` (created)
- Configured for local NIM deployment by default
- Set proper server URLs for local services
- Added model directory and user ID settings

### 3. `infrastructure/nim-services/docker-compose.nim.yml`
- Added default values for all environment variables
- Fixed volume mount specifications
- Updated user ID defaults

### 4. `docker-compose.yml`
- Made model engine configurable via environment variables
- Removed obsolete version field
- Maintained backward compatibility

### 5. New Scripts Created
- `deploy-local-nim.sh` - Local NIM deployment for Linux/macOS
- `deploy-local-nim.bat` - Local NIM deployment for Windows  
- `configure.sh` - Configuration helper script

### 6. `README.md`
- Added local NIM deployment instructions
- Added configuration examples for both deployment modes
- Added troubleshooting section for NIM-specific issues

## Deployment Options

### Option 1: Cloud Deployment (NVIDIA AI Endpoints)
```bash
# Configure for cloud
./configure.sh cloud

# Set API key
export NVIDIA_API_KEY="nvapi-your-key-here"

# Deploy
docker compose up -d --build
```

### Option 2: Local NIM Deployment
```bash
# Configure for local NIM
./configure.sh local-nim

# Set API keys
export NGC_API_KEY="your-ngc-api-key-here"
export NVIDIA_API_KEY="nvapi-your-key-here"

# Deploy with local NIM
./deploy-local-nim.sh
```

## Requirements for Local NIM

### Hardware
- NVIDIA GPU with 16GB+ VRAM (recommended)
- 32GB+ system RAM
- 50GB+ free disk space (for model downloads)

### Software
- Docker with NVIDIA runtime support
- NVIDIA Container Toolkit
- NGC API key for model downloads

## Verification

The configuration can be tested without starting services:

```bash
# Test cloud configuration
docker compose config

# Test local NIM configuration  
docker compose --profile local-nim config
```

Both commands should now complete without errors or warnings about missing environment variables.
