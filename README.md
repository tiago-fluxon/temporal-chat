# Chat with documents

> **⚠️ Disclaimer**: This is a pet project. The code is experimental and not production-ready. **Use at your own risk.**

## 🚀 Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Mandatory: Edit .env - add your OPENAI_API_KEY or CLAUDE_API_KEY
# Optional: change DOCUMENTS_DIR (defaults to ~/Desktop)

# 2. Start the system
docker compose up -d

# 3. Access the UI
open http://localhost:3000
```

## 📁 Project Structure

```
worker-stream/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app
│   │   └── routes/
│   │       └── chat.py          # SSE streaming endpoint
│   ├── temporal/
│   │   ├── workflows/
│   │   │   └── llm_chat_workflow.py  # Main workflow
│   │   ├── activities/
│   │   │   ├── document_activities.py
│   │   │   ├── prompt_activities.py
│   │   │   └── llm_activities.py     # LLM streaming
│   │   └── workers/
│   │       └── stream_worker.py      # Worker process
│   ├── llm/                     # LLM adapters (OpenAI/Claude)
│   ├── security/                # Path validation, prompt guard
│   └── document_processor/      # PDF/text readers
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ChatInterface.tsx
│       │   └── MessageStream.tsx
│       └── hooks/
│           └── useStreamingChat.ts   # SSE EventSource
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml           # 5 services
├── .env.example                 # Configuration template
└── requirements.txt             # Python dependencies
```

---

## 🔧 Configuration

### Environment Variables

```bash
# LLM API Keys (at least one required)
OPENAI_API_KEY=sk-proj-your-key-here
CLAUDE_API_KEY=sk-ant-your-key-here

# LLM Provider Selection
LLM_PROVIDER=openai  # or 'claude'

# Documents Directory (NEW - configurable directory path)
DOCUMENTS_DIR=~/Desktop  # Change to any directory you want to process
# Note: On macOS, some directories require Docker Desktop permissions
# Settings > Resources > File Sharing

# Temporal Configuration
TEMPORAL_ADDRESS=temporal:7233
TEMPORAL_NAMESPACE=default
TASK_QUEUE=chat-queue

# API Configuration
PORT=8000
CORS_ORIGINS=*  # For production: https://yourdomain.com

# Development
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
```

### Changing Document Directory

The application can process files from any directory by setting `DOCUMENTS_DIR`:

```bash
# Option 1: Edit .env file
echo "DOCUMENTS_DIR=~/Documents/my-docs" >> .env
docker compose down && docker compose up -d

# Option 2: Override on command line
DOCUMENTS_DIR=~/Documents/my-docs docker compose up -d

# Option 3: Export environment variable
export DOCUMENTS_DIR=~/Documents/my-docs
docker compose up -d
```

**macOS Permission Note:**
- Desktop and Downloads work by default
- Other directories may require explicit permission:
  1. Open Docker Desktop
  2. Go to Settings > Resources > File Sharing
  3. Add your directory path
  4. Click "Apply & Restart"

### Switching LLM Providers

The system supports **Claude** (default) and **OpenAI**. Only one provider is active at a time.

**To use Claude (default):**
```bash
# .env file
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-your-key-here
# OPENAI_API_KEY not required
```

**To use OpenAI:**
```bash
# .env file
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-your-key-here
# CLAUDE_API_KEY not required
```

**After changing provider:**
```bash
docker compose down
docker compose up -d
```

**Verify active provider in worker logs:**
```bash
docker compose logs worker | grep "LLM Provider"
# Output: LLM Provider: openai (or claude)
# Output: LLM Model: gpt-4o (or claude-3-5-sonnet-20241022)
```

### Workflow Parameters

```python
# backend/temporal/workflows/llm_chat_workflow.py
max_files: int = 10                # Files to process per request
max_file_size_mb: int = 10         # Max size per file
max_chars_per_file: int = 2000     # Chars per file (token management)
llm_max_tokens: int = 4096         # LLM response length
```

---

## 🐳 Services

The system runs 5 Docker services:

| Service | Port | Description |
|---------|------|-------------|
| **postgresql** | 5432 | Temporal database |
| **temporal** | 7233, 8233 | Workflow engine + UI |
| **worker** | - | Executes workflows/activities |
| **api** | 8000 | FastAPI backend (SSE streaming) |
| **frontend** | 3000 | React UI (nginx) |

**Access Points**:
- Frontend UI: http://localhost:3000
- API: http://localhost:8000
- Temporal UI: http://localhost:8233

---

## 🧪 Testing

### Manual Testing

```bash
# 1. Start services
docker compose up

# 2. Test API directly
curl -N "http://localhost:8000/api/chat?query=What%20files%20are%20there?&doc_path=/"

# 3. Test frontend
open http://localhost:3000
# Type a question about your Desktop files
```

### Health Check

```bash
$ curl http://localhost:8000/health
{
  "status": "healthy",
  "temporal": true,
  "streaming": "native_temporal"
}
```

### Check Logs

```bash
# Worker logs
docker compose logs worker --tail=50

# API logs
docker compose logs api --tail=50

# All services
docker compose logs --tail=100
```

---

## 📊 How It Works

### 1. User Asks Question

User types: "What files mention 'budget'?"

### 2. Frontend Sends Request

```typescript
// frontend/src/hooks/useStreamingChat.ts
const params = new URLSearchParams({
  query: "What files mention 'budget'?",
  doc_path: "/"
})
const eventSource = new EventSource(`/api/chat?${params}`)
```

### 3. API Starts Workflow

```python
# backend/api/routes/chat.py
handle = await client.start_workflow(
    LLMChatWorkflow.run,
    ChatRequest(user_query=query, doc_path=doc_path),
    id=workflow_id,
    task_queue="chat-queue"
)
```

### 4. Workflow Executes Activities

```python
# backend/temporal/workflows/llm_chat_workflow.py
# Scan directory
file_paths = await workflow.execute_activity("scan_directory", ...)

# Read documents (parallel)
documents = await asyncio.gather(*read_tasks)

# Build safe prompt
prompt = await workflow.execute_activity("build_safe_prompt", ...)

# Stream LLM
llm_result = await workflow.execute_activity("stream_llm_native", ...)
```

### 5. LLM Activity Signals Tokens

```python
# backend/temporal/activities/llm_activities.py
async for chunk in self.llm.stream_completion(prompt, ...):
    batch.append(chunk.content)
    if len(batch) >= batch_size:
        for token in batch:
            await handle.signal("receive_token", token)
```

### 6. API Polls Workflow State

```python
# backend/api/routes/chat.py
while True:
    state = await handle.query("get_stream_state")
    new_tokens = state.tokens[seen_tokens:]
    for token in new_tokens:
        yield token  # SSE: data: {token}
```

### 7. Frontend Displays Tokens

```typescript
// frontend/src/hooks/useStreamingChat.ts
eventSource.onmessage = (event) => {
  const token = event.data
  setMessages(prev => prev.map(msg =>
    msg.id === assistantMessageId
      ? { ...msg, content: msg.content + token }
      : msg
  ))
}
```

---

## 🚨 Troubleshooting

### "Connection refused"
```bash
# Check services are running
docker compose ps

# Restart services
docker compose restart
```

### "No files found in specified directory"

This is **expected behavior** when a directory contains no supported file types.

**Supported file types:** `.txt`, `.md`, `.pdf`, `.json`, `.csv`

**Troubleshooting:**
```bash
# Check directory is mounted correctly
docker compose exec worker ls /documents

# Verify files exist in your DOCUMENTS_DIR
ls ~/Desktop  # or your configured directory

# Check if files have supported extensions
ls ~/Desktop/*.txt ~/Desktop/*.pdf ~/Desktop/*.md

# Verify Docker has access to the directory (macOS)
# Docker Desktop > Settings > Resources > File Sharing
```

**Common causes:**
- Directory only contains unsupported file types (.mov, .jpg, .exe, etc.)
- Empty directory
- Docker doesn't have permission to access the directory (macOS)

### "Token limit exceeded"
```bash
# System processes max 10 files × 2000 chars
# Reduce file count or use subdirectories
```

### "Activity task failed"
```bash
# Check worker logs for actual error
docker compose logs worker --tail=100
```

---

## 📝 License

MIT License

---
