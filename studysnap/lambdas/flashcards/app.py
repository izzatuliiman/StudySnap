import base64
import boto3
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)
bedrock = boto3.client("bedrock-runtime", region_name="ap-southeast-1")
MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}

SYSTEM_PROMPT = (
    "You are a helpful study assistant. A student has provided their lecture notes. "
    "Based on these notes, generate exactly 5 flashcards covering the key concepts. "
    "Format each flashcard like this:\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "🃏 FLASHCARD 1 of 5\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "📖 HOW TO USE: Read the question, think of your answer, then scroll down to check!\n\n"
    "❓ QUESTION:\n"
    "Write the question here\n\n"
    "⬇️ Think of your answer first, then reveal below...\n"
    "· · · · · · · · · · · · · · · ·\n"
    "💡 ANSWER:\n"
    "Write the answer here\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Repeat this format for all 5 flashcards, numbering them 1 of 5 through 5 of 5. "
    "Replace all placeholder text with real content from the lecture notes. "
    "Cover a broad range of key topics. Keep answers clear and concise."
)


def generate(data: dict):
    file_data = data.get("file_data")

    if file_data:
        raw_bytes = base64.b64decode(file_data)
        content = [
            {
                "document": {
                    "format": "pdf",
                    "name": "lecture_notes",
                    "source": {"bytes": raw_bytes},
                }
            },
            {"text": "Please create exactly 5 flashcards from the lecture notes in the document above."},
        ]
    else:
        content = [{"text": "Please create exactly 5 flashcards from the provided lecture notes."}]

    messages = [{"role": "user", "content": content}]

    response = bedrock.converse_stream(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={"maxTokens": 2048, "temperature": 0.5},
    )

    for event in response["stream"]:
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                yield delta["text"]


@app.route("/", methods=["OPTIONS"])
def options():
    return Response("", status=200, headers=CORS_HEADERS)


@app.route("/", methods=["POST"])
def handler():
    data = request.get_json(force=True, silent=True) or {}

    def streamer():
        for chunk in generate(data):
            yield chunk

    resp = Response(
        stream_with_context(streamer()),
        content_type="text/plain; charset=utf-8",
    )
    for k, v in CORS_HEADERS.items():
        resp.headers[k] = v
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
