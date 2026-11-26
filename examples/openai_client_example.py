"""Example showing drop-in compatibility with the official OpenAI Python SDK."""

from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="freevoice-local",
)

with client.audio.speech.with_streaming_response.create(
    model="kokoro-82m",
    voice="af_heart",
    input="Hello from FreeVoice! This uses the exact OpenAI audio speech client interface.",
    response_format="mp3",
) as response:
    response.stream_to_file("openai_sdk_test.mp3")

print("Saved openai_sdk_test.mp3")