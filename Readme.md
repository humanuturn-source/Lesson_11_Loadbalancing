

# Install Instructions

Let’s go step-by-step through setting up this local multimodal AI agent from scratch using 100% open-source tools.
Note on OS Compatibility: The steps below show exact terminal commands for macOS. If you are using Linux, commands are nearly identical. If you are on Windows, use PowerShell or Git Bash


## Step 1: Install Ollama & Pull Local Models

Install Ollama to host your models locally, then pull Google DeepMind’s Gemma 4 (or any preferred multimodal vision model, like LLaVA or MiniCPM).

1.	Install Ollama:
⚬	macOS / Linux: Download from ollama.com or run:

    ```bash
    brew install ollama
    ```
⚬	Windows: Download and run the setup installer from ollama.com.

2.	Pull the Local Gemma 4 Model:
Open your terminal and run:

    ```bash
    ollama pull gemma:2b
    ollama pull gemma4

    ```
(If your script uses a specific model variant or swap model—e.g., llava or mini-cpm—simply replace gemma4 in your Python script's model_name parameter).

## Step 2: Create a Python Virtual Environment

Keep your dependencies isolated by creating a clean virtual environment:

    ```bash
    # 1. Navigate to your project folder
    cd ai_app

    # 2. Create the virtual environment
    python3 -m venv venv

    # 3. Activate the virtual environment
    # macOS / Linux:
    source venv/bin/activate

    # Windows (PowerShell):
    # .\venv\Scripts\Activate.ps1
    ```

## Step 3: Install Required Dependencies
Install the required libraries inside your activated virtual environment:

    ```bash
    pip install --upgrade pip
    pip install ollama pypdf sqlite3-binary fastapi uvicorn pydantic

    ```
## Step 4: Initialize the SQLite Database & Run

Initialize the Database:

    ```bash
    python3 sqlite.py

    ```

### Step 5: Create MCP Servers

Copy mcp_servers.py from the link in description and run

    ```bash
    python mcp_servers.py
    ```

### Step 6: Source documents for retuen policy and working hours

Copy the following PDF documents from the GitHub repositoey

    supermarket_return_policy.pdf    
    supermarket_working_hours.pdf

### Step 7: Create multi-agents

Copy agent_mcp.py from the GitHub repositoey and run

    ```bash
    python agent_mcp.py
    ```

### Step 8: Run Server wrapper

Start the Multi-Agent API Wrapper and keep the window open.

    ```bash
    python server_wrapper.py

    ```
### Step 9: Run Open WebUI in Docker

   ```bash
        docker run -d -p 3000:8080 \
        --add-host=host.docker.internal:host-gateway \
        -v open-webui:/app/backend/data \
        --name open-webui \
        --restart always \
        ghcr.io/open-webui/open-webui:main

   ```

### Step 10: Connect Open WebUI to Your Local Agent

1.	Open your browser and go to http://localhost:3000.
2.	Create your local admin account upon first login.
3.	Click on Admin Panel (bottom-left avatar) -> Settings -> Connections.
4.	In the OpenAI API section:
    ⚬	Set API Base URL to: http://host.docker.internal:8000/v1
    ⚬	Set API Key to: sk-local (or any placeholder string).
        5.	Click the Refresh/Save icon. You will see supermarket-agent appear in the available model dropdown list.

### Step 11: Application Testing

1.	In Open WebUI, select supermarket-agent from the model picker dropdown at the top.
2.	Drag and drop any image (Example: picture of Apple) directly into the chat prompt box and enter the prompt.
3.	Open WebUI sends the image payload over HTTP to server_wrapper.py.
4.	Your agent_mcp.py routes the image through agent_vision_specialist, executes any SQLite/PDF MCP tool lookups, and returns the response back to the Open WebUI interface.
5. Check the response

-------------------
