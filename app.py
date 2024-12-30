from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Replace with your OpenAI API key
OPENAI_API_KEY = "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"

def extract_video_id(url):
    try:
        if 'youtu.be/' in url:
            return url.split('youtu.be/')[1].split('?')[0]
        elif 'youtube.com/watch?v=' in url:
            return url.split('youtube.com/watch?v=')[1].split('&')[0]
        return None
    except:
        return None

@app.route('/api/transcript', methods=['POST'])
def get_transcript():
    try:
        data = request.get_json()
        url = data['url']
        
        # Get video ID
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
            
        # Get transcript from YouTube
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Format with timestamps
        formatted_text = ""
        for entry in transcript_data:
            time = int(entry['start'])
            minutes = time // 60
            seconds = time % 60
            formatted_text += f"[{minutes:02d}:{seconds:02d}] {entry['text']}\n"
        
        # Send to GPT-4
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a transcript editor. Improve the following transcript by adding proper punctuation and formatting while keeping the timestamps."
                },
                {
                    "role": "user",
                    "content": formatted_text
                }
            ],
            "temperature": 0.7
        }
        
        gpt_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        improved_transcript = gpt_response.json()['choices'][0]['message']['content']
        
        return jsonify({
            'original': formatted_text,
            'improved': improved_transcript
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)