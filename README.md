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

# Ring ML Person Detector

A Python application that filters Ring camera images to keep only those containing people using YOLOv8 object detection.

<details>
  <summary style="font-size:1.2em;">Table of Contents</summary>
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Code-Style](#code-style)
- [Getting Started](#getting-started)
  - [Prerequisties](#prerequisties)
  - [Initialize repository](#initialize-repository)
- [Usage](#usage)
  - [Running the API](#running-the-api)
  - [API Endpoints](#api-endpoints)
  - [Response Format](#response-format)
- [Known Issues](#known-issues)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
</details>

## Code-Style

<!-- TBD -->

## Getting Started

### Prerequisties

- [pre-commit][pre-commit-url]
- [uv][uv-url]

### Initialize repository

pre-commit framework needs to get initialized.

```shell
task pre-commit:init
```

install dependencies

```shell
uv sync
```

activate venv

```shell
source .venv/bin/activate
```

## Usage

### Running the API

Run the API server:

```shell
uv run src/inference.py
```

This will start the API server at `http://localhost:8000`.

### API Endpoints

#### Health Check

```console
GET /
```

Returns a simple health check response.

#### Person Detection

```console
POST /detect
```

Submit an image file to check if a person is present.

Example with curl:

```shell
curl -X POST http://localhost:8000/detect \
  -F "file=@image.jpg"
```

### Response Format

```json
{
  "filename": "image.jpg",
  "person_detected": true,
  "confidence": 0.92,
  "num_persons": 1,
  "person_boxes": [
    {
      "confidence": 0.92,
      "bbox": [120.5, 250.8, 380.2, 520.6]
    }
  ]
}
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
