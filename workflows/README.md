### README: Pixelle-Video Windows Setup and Usage Guide

This guide details the steps to install and run Pixelle-Video on a Windows system, including prerequisites, server setup, and workflow dependencies.

---

#### **1. Installation and Environment Setup**

**1.1 Install ffmpeg**
First, you need to install `ffmpeg` using Scoop.
Open **Windows PowerShell** and execute the following commands:
```powershell
# Set execution policy to allow script execution (if not already set)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install Scoop (if not already installed)
irm get.scoop.sh | iex

# Install ffmpeg via Scoop
scoop install ffmpeg
```

**1.2 Clone and Set Up the Pixelle-Video Project**
```powershell
# Clone the repository
git clone https://github.com/AIDC-AI/Pixelle-Video.git

# Navigate into the project directory
cd Pixelle-Video

# Run the main application using Streamlit with uv
uv run streamlit run web/app.py
```

**1.3 Install Additional Dependencies**
Install the `httpx` library with SOCKS proxy support:
```powershell
uv pip install "httpx[socks]"
```

---

#### **2. Configuration**

*   **Choose LLM Provider**: In the application, select **deepseek** as your LLM provider for text generation tasks.
*   **Set Up ComfyUI Server**: You need to have a running ComfyUI server instance. The application will interact with this server to execute generation workflows.

---

#### **3. Workflow Dependencies**

Workflows and dependencies are managed in the `Pixelle-MCP` repository.
*   Dependencies for the workflows are documented here:
    https://github.com/svjack/Pixelle-MCP/tree/main/generic_workflows
*   For Pixelle-Video to use these workflows, place the relevant files into the following local directory:
    `Pixelle-Video\workflows\selfhost`

---

#### **4. Key ComfyUI Workflows for Rapid Content Creation**

The following workflows should be available in your ComfyUI server and are used for different stages of creation:

**4.1 Generate Image**
*   Workflow: **`image_P_vid_z_image_turbo_text_to_image_api`**
*   Purpose: Creates an initial image from a text prompt.

**4.2 Generate Voiceover**
*   Workflow: **`tts_P_Vid_Qwen3_TTS_Voice_Clone_api`**
*   Purpose: Generates a narrated voiceover from text.
*   Note: This works in conjunction with the music generation workflow `ace_step_1_5_text_to_music` from `Pixelle-MCP/data/custom_workflows/` to create background music. put it in bgm dir

**4.3 Motion Transfer**
*   Workflow: **`af_P_vid_wan21_video_pose_transfer`**
*   Purpose: Applies pose or motion transfer to a video.

**4.4 Image-to-Video**
*   Usage: The **Pixelle-MCP** framework is used to handle image-to-video generation tasks. Please refer to its documentation for specific workflow names and usage.
