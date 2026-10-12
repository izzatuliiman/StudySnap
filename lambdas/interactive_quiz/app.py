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
    "You are a quiz master. The student has uploaded lecture notes — use them as your source "
    "material to generate quiz questions.\n\n"
    "Generate 5 multiple-choice quiz questions based on the lecture notes. "
    "Do not reveal the correct answers until the student has answered. "
    "Present one question at a time. Start by presenting Question 1 with 4 options (A, B, C, D) "
    "and wait for the user's answer before proceeding. "
    "After the user answers, tell them if they are correct or not, briefly explain the right answer, "
    "then move on to the next question. "
    "After all 5 questions, show a final score out of 5. "
    "Then ask the user to rate their confidence level on this topic from 1 to 5, "
    "where 1 means very unsure and 5 means very confident. "
    "Based on their rating, provide personalised study tips and recommendations."
)


def generate(data: dict):
    """Build full conversation history and stream the next assistant reply."""
    history = data.get("history", [])   # [{role, content}] from previous turns
    new_message = data.get("message", "")
    file_data = data.get("file_data")

    messages = []

    # Replay history (plain text turns)
    for turn in history:
        role = turn.get("role", "user")
        text = turn.get("content", "")
        messages.append({"role": role, "content": [{"text": text}]})

    # Build new user message — attach document on first turn only
    if file_data and not history:
        raw_bytes = base64.b64decode(file_data)
        content = [
            {
                "document": {
                    "format": "pdf",
                    "name": "lecture_notes",
                    "source": {"bytes": raw_bytes},
                }
            },
            {"text": new_message},
        ]
    else:
        content = [{"text": new_message}]

    messages.append({"role": "user", "content": content})

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
