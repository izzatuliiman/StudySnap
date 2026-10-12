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
    "You are a helpful study assistant. A student has uploaded their lecture notes. "
    "Analyse the key concepts in these notes. Tag each main concept with a difficulty level "
    "using this format:\n\n"
    "🟢 EASY — Concept name: One sentence explaining why it is straightforward.\n"
    "🟡 MEDIUM — Concept name: One sentence explaining why it needs some attention.\n"
    "🔴 HARD — Concept name: One sentence explaining why it is challenging.\n\n"
    "Tag at least 5 concepts. End with a short tip on where the student should focus most of "
    "their study time."
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
            {"text": "Please tag the key concepts from the lecture notes in the document above with difficulty levels."},
        ]
    else:
        content = [{"text": "Please tag the key concepts from the provided lecture notes with difficulty levels."}]

    messages = [{"role": "user", "content": content}]

    response = bedrock.converse_stream(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={"maxTokens": 1024, "temperature": 0.5},
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
