# BuddyImagine

BuddyImagine is a Telegram bot that leverages the power of [FAL AI](https://fal.ai) for high-quality image generation and Cloudflare R2 for efficient storage.

## Features

*   **🤖 AI-Powered Generation**: Uses an intelligent agent to understand your prompts.
*   **🎨 Multiple Models**: Supports various state-of-the-art models like Flux, SDXL, Recraft, and more.
*   **☁️ Cloud Storage**: Automatically saves all generated images to Cloudflare R2.
*   **🔍 Model Discovery**: Built-in fuzzy search to find the perfect model for your needs.

## Commands

*   `/start` - Initialize the bot and see the welcome message.
*   `/generate <prompt>` - Generate an image. You can specify the model naturally in the prompt (e.g., "Generate a cyberpunk city using Flux").
*   `/models [query]` - List available models or search for specific ones (e.g., `/models flux`).
*   `/help` - Show the help message.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd BuddyImagine
    ```

2.  **Install dependencies:**
    This project uses `uv` for dependency management.
    ```bash
    uv sync
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the root directory with the following variables:

    ```env
    BOT_TOKEN=your_telegram_bot_token
    OPENAI_API_KEY=your_openai_api_key  # For the agent logic
    FAL_KEY=your_fal_ai_key             # For image generation
    
    # Cloudflare R2 Configuration
    R2_ACCESS_KEY_ID=your_r2_access_key
    R2_SECRET_ACCESS_KEY=your_r2_secret_key
    R2_BUCKET_NAME=your_bucket_name
    R2_ENDPOINT_URL=your_r2_endpoint_url
    ```

4.  **Run the Bot:**
    ```bash
    uv run main.py
    ```

## Development

*   **Run Tests:**
    ```bash
    uv run pytest
    ```
*   **Type Check:**
    ```bash
    uv run mypy .
    ```

## Architecture

*   **`main.py`**: Entry point, sets up the bot and polling.
*   **`handlers.py`**: Telegram message handlers (commands).
*   **`agent.py`**: logic using `pydantic-ai` to process prompts and select tools.
*   **`services/`**:
    *   `fal.py`: Service for interacting with FAL AI API.
    *   `r2.py`: Service for uploading/downloading files to Cloudflare R2.

     docker-compose down && docker-compose build --no-cache && docker-compose up -d