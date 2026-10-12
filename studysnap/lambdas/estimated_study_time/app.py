import json
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
    "Based on the complexity, length, and density of the content, estimate how long it would "
    "take an average student to revise this topic thoroughly. Break it down like this:\n\n"
    "⏱️ Quick Skim: X minutes\n"
    "📖 Active Reading: X minutes\n"
    "🃏 Flashcard Review: X minutes\n"
    "📝 Quiz Practice: X minutes\n"
    "⏳ Total Estimated Time: X minutes\n\n"
    "Briefly explain your reasoning in 1-2 sentences."
)


def build_messages(data: dict) -> list:
    """Build Converse API messages list with optional document block."""
    file_data = data.get("file_data")
    file_mime = data.get("file_mime", "application/pdf")

    if file_data:
        content = [
            {
                "document": {
                    "format": "pdf",
                    "name": "lecture_notes",
                    "source": {
                        "bytes": file_data.encode("utf-8")
                        if isinstance(file_data, str)
                        else file_data,
                    },
                }
            },
            {
                "text": "Please analyse the lecture notes in the document above and estimate the study time as instructed."
            },
        ]
    else:
        content = [{"text": "Please estimate the study time for the provided lecture notes."}]

    return [{"role": "user", "content": content}]


def generate(data: dict):
    """Stream response tokens using Converse Stream API."""
    import base64

    file_data = data.get("file_data")
    file_mime = data.get("file_mime", "application/pdf")

    if file_data:
        # Converse API expects raw bytes for document source
        raw_bytes = base64.b64decode(file_data)
        content = [
            {
                "document": {
                    "format": "pdf",
                    "name": "lecture_notes",
                    "source": {"bytes": raw_bytes},
                }
            },
            {
                "text": "Please analyse the lecture notes in the document above and estimate the study time as instructed."
            },
        ]
    else:
        content = [{"text": "Please estimate the study time for the provided lecture notes."}]

    messages = [{"role": "user", "content": content}]

    response = bedrock.converse_stream(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
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
