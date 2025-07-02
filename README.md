<!-- markdownlint-disable MD041 -->
<!-- markdownlint-disable MD033 -->
<!-- markdownlint-disable MD028 -->

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

[![pre-commit][pre-commit-shield]][pre-commit-url]
[![taskfile][taskfile-shield]][taskfile-url]

# ML Detector

A Python application that filters images to keep only those containing the objects specified using YOLO object detection.

<details>
  <summary style="font-size:1.2em;">Table of Contents</summary>
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Code-Style](#code-style)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Initialization](#initialization)
- [Configuration](#configuration)
  - [Configuration File](#configuration-file)
  - [Environment Variables](#environment-variables)
  - [Model Configuration](#model-configuration)
- [Usage](#usage)
  - [Running the API](#running-the-api)
  - [Using Docker](#using-docker)
  - [API Endpoints](#api-endpoints)
  - [Response Format](#response-format)
  - [Testing the API](#testing-the-api)
- [Known Issues](#known-issues)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
</details>

## Code-Style

<!-- TBD -->

## Getting Started

### Prerequisites

- **[uv][uv-url]**: Fast Python package manager
- **[pre-commit][pre-commit-url]**: Git hooks framework
- **[Task][taskfile-url]**: Task runner (optional)

### Initialization

1. **Initialize pre-commit hooks**:

   ```shell
   task pre-commit:init
   ```

2. **Install dependencies**:

   Production dependencies:

   ```shell
   uv sync
   ```

   Include development dependencies:

   ```shell
   uv sync --dev
   ```

   For CPU inference:

   ```shell
   uv sync --extra cpu
   ```

   For Intel XPU inference:

   ```shell
   uv sync --extra xpu
   ```

3. **Activate virtual environment**:

   ```shell
   source .venv/bin/activate
   ```

## Configuration

### Configuration File

The application uses `config/configuration.yaml` for all settings, see for example configuration.

### Environment Variables

- **`RING_DETECTOR_CONFIG`**: Path to configuration file (default: `config/configuration.yaml`)

Example:

```shell
export RING_DETECTOR_CONFIG="/path/to/custom/config.yaml"
```

### Model Configuration

**Available Model Sizes**:

- **nano**: Fastest, lowest accuracy (~6MB)
- **small**: Good balance of speed/accuracy (~22MB) - **Recommended**
- **medium**: Higher accuracy, slower (~50MB)
- **large**: High accuracy, much slower (~100MB)
- **xlarge**: Highest accuracy, slowest (~220MB)

**Device Options**:

- **cpu**: Universal compatibility
- **cuda**: NVIDIA GPU acceleration
- **mps**: Apple Silicon GPU acceleration

## Usage

### Running the API

Run the API server:

```shell
export RING_DETECTOR_CONFIG="config/configuration.yaml"
export YOLO_CONFIG_DIR="/app/yolo" # writeable
uv run src/inference.py
```

The API server will start at `http://localhost:8000`.

### Using Docker

Build the Docker image:

```shell
docker buildx build --progress=plain -t ring-person-detector .
```

Run the Docker container:

```shell
docker run --rm -it \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/models:/app/models \
  ring-person-detector
```

### API Endpoints

#### Health Checks

**Service Information**:

```shell
GET /
```

Returns service metadata including version and status.

**Liveness Probe**:

```shell
GET /livez
```

Kubernetes liveness probe. Returns `200` if the service process is alive.

**Readiness Probe**:

```shell
GET /readyz
```

Kubernetes readiness probe. Returns `200` when service is ready to handle requests.
Returns `503` during initialization, shutdown, or when dependencies are unavailable.

#### Person Detection

**Detect Person in Image**:

```shell
POST /detect
```

**Parameters**:

- `file`: Image file (multipart/form-data)
- Supported formats: JPG, JPEG, PNG, BMP, TIFF

**Example with curl**:

```shell
curl -X POST http://localhost:8000/detect \
  -F "file=@/path/to/image.jpg"
```

### Response Format

**Successful Detection**:

```json
{
  "filename": "image.jpg",
  "person_detected": true,
  "confidence": 0.89,
  "num_persons": 2,
  "person_boxes": [
    {
      "confidence": 0.89,
      "bbox": [120.5, 250.8, 380.2, 520.6]
    },
    {
      "confidence": 0.76,
      "bbox": [450.1, 180.3, 600.7, 480.9]
    }
  ]
}
```

**No Person Detected**:

```json
{
  "filename": "image.jpg",
  "person_detected": false,
  "confidence": 0.0,
  "num_persons": 0,
  "person_boxes": []
}
```

**Response Fields**:

- `filename`: Original filename or "uploaded_image"
- `person_detected`: Boolean indicating if any person was found
- `confidence`: Highest confidence score among detected persons
- `num_persons`: Total number of persons detected
- `person_boxes`: Array of detection results with confidence and bounding box coordinates

**Bounding Box Format**: `[x1, y1, x2, y2]` where:

- `x1, y1`: Top-left corner coordinates
- `x2, y2`: Bottom-right corner coordinates

### Testing the API

**Basic health check**:

```shell
curl http://localhost:8000/
```

**Liveness probe**:

```shell
curl http://localhost:8000/livez
```

**Readiness probe**:

```shell
curl http://localhost:8000/readyz
```

## Known Issues

<!-- TBD -->

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

<!-- Links -->

[uv-url]: https://github.com/astral-sh/uv

<!-- Badges -->

[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit
[pre-commit-url]: https://github.com/pre-commit/pre-commit
[taskfile-url]: https://taskfile.dev/
[taskfile-shield]: https://img.shields.io/badge/Taskfile-Enabled-brightgreen?logo=task
