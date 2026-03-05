<div id="top">

<!-- HEADER STYLE: CLASSIC -->
<div align="center">


# MULTI TENANT RAG_APP

<em>Transform Data Into Actionable Insights Instantly</em>

<!-- BADGES -->
<img src="https://img.shields.io/github/last-commit/Al3za/RAG_APP?style=flat&logo=git&logoColor=white&color=0080ff" alt="last-commit">
<img src="https://img.shields.io/github/languages/top/Al3za/RAG_APP?style=flat&color=0080ff" alt="repo-top-language">
<img src="https://img.shields.io/github/languages/count/Al3za/RAG_APP?style=flat&color=0080ff" alt="repo-language-count">

<em>Built with the tools and technologies:</em>

<img src="https://img.shields.io/badge/Markdown-000000.svg?style=flat&logo=Markdown&logoColor=white" alt="Markdown">
<img src="https://img.shields.io/badge/Python-3776AB.svg?style=flat&logo=Python&logoColor=white" alt="Python">

</div>
<br>

---

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Usage](#usage)
    - [Testing](#testing)

---

## Overview

**MULTI TENANT RAG_APP** is an advanced developer toolset designed to facilitate efficient document ingestion, semantic chunking, and retrieval-augmented generation workflows. It streamlines the process of preparing, storing, and querying complex PDFs, enabling the development of intelligent, context-aware NLP applications.

**Why RAG_APP?**

This project aims to optimize document processing pipelines for accuracy and scalability. The core features include:
-  **Storage:** Pdf stored in **s3** bucket
-  **Multi Tenant** Pdf related to 'logged in' in user email(hashed before uploading)
- 🧩 **Puzzle Piece:** Semantic chunking and cross-page overlap to preserve context across multi-page documents.
- 🧹 **Broom:** PDF text cleaning and normalization for high-quality downstream analysis.
- 🔐 **Lock:** Secure JWT-based user authentication and management.
- 🚀 **Rocket:** Integration with Pinecone for fast, scalable semantic search.
- 📊 **Bar Chart:** API endpoints for health checks, upload status, and interactive chat.
- ⚡ **Lightning Bolt:** Redis-powered caching and rate limiting for performance and stability.

---

## Getting Started

### Prerequisites

This project requires the following dependencies:

- **Programming Language:** Python
- **Package Manager:** Pip

### Installation

Build RAG_APP from the source and install dependencies:

1. **Clone the repository:**

    ```sh
    ❯ git clone https://github.com/Al3za/RAG_APP
    ```

2. **Navigate to the project directory:**

    ```sh
    ❯ cd RAG_APP
    ```

3. **Install the dependencies:**

**Using [pip](https://pypi.org/project/pip/):**

```sh
❯ pip install -r requirements.txt
```

### Usage

Run the project with:

**Using [pip](https://pypi.org/project/pip/):**

```sh
docker run -d --name my-redis -p 6379:6379 redis (To crete a docker container with the latest redis image pulled from docker hub)

then run the container by name:
docker start my-redis

and finally start the app:
uvicorn app.main:app --reload
```



<div align="left"><a href="#top">⬆ Return</a></div>

---
