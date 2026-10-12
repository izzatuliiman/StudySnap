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
    "For every abstract or theoretical concept mentioned in these notes, provide a relatable "
    "real-world example to make it easier to understand. Format each entry like this:\n\n"
    "💡 CONCEPT NAME\n"
    "What it means: Write a brief, simple explanation.\n"
    "Real-world example: Describe a practical, everyday scenario that illustrates this concept clearly.\n\n"
    "Cover all major abstract concepts in the notes. Make the examples vivid and easy to relate to."
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
            {"text": "Please provide real-world examples for all abstract concepts in the lecture notes document above."},
        ]
    else:
        content = [{"text": "Please provide real-world examples for the abstract concepts in the provided lecture notes."}]

    messages = [{"role": "user", "content": content}]

    response = bedrock.converse_stream(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={"maxTokens": 2048, "temperature": 0.7},
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
