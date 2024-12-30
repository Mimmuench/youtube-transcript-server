from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from flask_cors import CORS
import re
import os
import logging
import asyncio
import tiktoken
from openai import AsyncOpenAI, OpenAIError
from dotenv import load_dotenv
from auth import require_custom_authentication  # Ensure you have your auth.py file correctly set up

# Load environment variables from the .env file
load_dotenv()

# Retrieve the OpenAI API key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")

# Check if the API key is loaded correctly (optional, for debugging)
if openai_api_key is None:
    raise ValueError("API key not found in environment variables")

# Initialize the OpenAI client with the API key
client = AsyncOpenAI(api_key=openai_api_key)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Flask application
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing (CORS)

def get_youtube_id(url):
    """Extract YouTube video ID from URL."""
    video_id = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return video_id.group(1) if video_id else None

def process_transcript(video_id):
    """Fetch the transcript for a YouTube video."""
    proxy_address = os.environ.get("PROXY")
    transcript = YouTubeTranscriptApi.get_transcript(video_id, proxies={"http": proxy_address, "https": proxy_address})
    full_text = ' '.join([entry['text'] for entry in transcript])
    return full_text

def chunk_text(text, max_tokens=16000):
    """Split the text into chunks of approximately max_tokens tokens."""
    tokenizer = tiktoken.encoding_for_model("gpt-4")  # Ensure this matches the correct OpenAI model you're using

    words = text.split()
    chunks = []
    current_chunk = []
    current_token_count = 0

    for word in words:
        word_token_count = len(tokenizer.encode(word + " "))

        if current_token_count + word_token_count > max_tokens:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_token_count = 0

        current_chunk.append(word)
        current_token_count += word_token_count

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

async def process_chunk(chunk):
    """Process a single chunk using GPT-4 for text improvement."""
    try:
        response = await client.chat.completions.create(
            model="gpt-4",  # Update to the correct GPT model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that improves text formatting and adds punctuation."},
                {"role": "user", "content": chunk}
            ]
        )
        return response.choices[0].message.content
    except OpenAIError as e:
        return f"OpenAI API error: {str(e)}"

async def improve_text_with_gpt4(text):
    """Improve the full transcript text using GPT-4."""
    if not client.api_key:
        return "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."

    chunks = chunk_text(text)
    tasks = [process_chunk(chunk) for chunk in chunks]
    improved_chunks = await asyncio.gather(*tasks)
    return ' '.join(improved_chunks)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Handle the POST request to transcribe a YouTube video."""
    youtube_url = request.json.get('url')
    if not youtube_url:
        return jsonify({"error": "No YouTube URL provided"}), 400

    video_id = get_youtube_id(youtube_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        logger.info(f"videoid = {video_id}")
        transcript_text = process_transcript(video_id)
        logger.info(f"Transcript text = {transcript_text}")
        improved_text = asyncio.run(improve_text_with_gpt4(transcript_text))

        return jsonify({"result": improved_text})

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route("/", methods=["GET"])
def home():
    """Home route for testing API status."""
    return "Hello, World!"

if __name__ == '__main__':
    # Get the PORT from environment variable or default to 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Retrieve specific environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
proxy = os.getenv("PROXY")
port = os.getenv("PORT")

# Check and print them to verify
print(f"OpenAI API Key: {openai_api_key}")
print(f"Proxy URL: {proxy}")
print(f"Port: {port}")

# Verify if .env was loaded successfully
if openai_api_key:
    print("dotenv loaded successfully!")
else:
    print("dotenv load failed!")