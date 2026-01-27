FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run with HTTP transport (Streamable HTTP + SSE)
# For STDIO transport: CMD ["python", "-m", "mcp_server", "--stdio"]
CMD ["python", "-m", "mcp_server", "--http"]
