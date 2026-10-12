import json
import base64
import random
import boto3

bedrock = boto3.client("bedrock-runtime", region_name="ap-southeast-1")
MODEL_ID = "amazon.nova-canvas-v1:0"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}

IMAGE_PROMPT_TEMPLATE = (
    "Create an adorable, cute illustration representing the main topic and key concepts from these "
    "lecture notes: {topic_hint}. "
    "Use a kawaii or chibi art style with soft pastel colors, friendly characters, and charming details. "
    "Include cute mascot-like characters or animals related to the subject matter, with big eyes and "
    "cheerful expressions. The overall feel should be warm, playful, and delightful while still being "
    "educational and relevant to the topic."
)

FALLBACK_PROMPT = (
    "Create an adorable, cute kawaii-style illustration of a student studying with books and notes. "
    "Use soft pastel colors, friendly chibi characters with big eyes, and cheerful expressions. "
    "The overall feel should be warm, playful, and educational."
)


def handler(event, context):
    # Handle CORS preflight
    http_method = event.get("httpMethod", "POST")
    if http_method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": "",
        }

    try:
        body = json.loads(event.get("body") or "{}")
        file_data = body.get("file_data")
        file_mime = body.get("file_mime", "application/pdf")

        # Build a topic hint from file name / content summary if available
        # Since Nova Canvas is text-to-image only, we use a text prompt.
        # For a richer prompt you could first call Claude to summarise the topic
        # from the document, but to keep this Lambda self-contained we use a
        # generic educational prompt that still references the uploaded material.
        topic_hint = body.get("topic_hint", "the uploaded lecture notes")
        image_prompt = IMAGE_PROMPT_TEMPLATE.format(topic_hint=topic_hint)

        seed = random.randint(0, 2147483647)

        nova_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": image_prompt,
                "negativeText": (
                    "ugly, blurry, low quality, dark, scary, violent, text, watermark, "
                    "realistic photo, 3d render"
                ),
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "width": 1280,
                "height": 720,
                "quality": "standard",
                "seed": seed,
            },
        }

        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(nova_body),
            contentType="application/json",
            accept="application/json",
        )

        result = json.loads(response["body"].read())
        images = result.get("images", [])

        if not images:
            raise ValueError("No images returned from Nova Canvas")

        return {
            "statusCode": 200,
            "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
            "body": json.dumps({"image_base64": images[0]}),
        }

    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }
