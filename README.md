# 📚 StudySnap — AI Study Assistant

StudySnap is a serverless AI study assistant that transforms PDF lecture notes into summaries, flashcards, key terms, real-world examples, difficulty tags, an interactive quiz, and a kawaii topic illustration — all powered by Amazon Bedrock.

---

## ✨ Features

| Widget | Description |
|---|---|
| 📄 PDF Upload | Drag-and-drop lecture notes (PDF, max 10 MB) |
| ⏱️ Estimated Study Time | AI-estimated revision breakdown |
| 📋 Bullet Point Summary | 5–7 key takeaways |
| 📌 Key Terms Glossary | Definitions + real-world examples |
| 💡 Real World Examples | Abstract concepts made concrete |
| 🎚️ Difficulty Level Tags | 🟢 Easy / 🟡 Medium / 🔴 Hard per concept |
| 🃏 Flashcards | 5 Q&A cards in a clear format |
| 🖼️ Topic Visual | Kawaii-style illustration (Nova Canvas) |
| 🤖 Interactive Quiz | 5-question chatbot with score + study tips |
| 🎨 Dynamic Themes | UI palette auto-matches lecture topic |
| 📂 Session History | Last 20 sessions saved in localStorage |

---

## 🏗️ Architecture

```
Browser (S3 static site)
    │
    ├── fetch() streaming ──► 7 × Lambda Function URL (Flask + LambdaAdapterLayerX86)
    │                              └── Bedrock: global.anthropic.claude-haiku-4-5-20251001-v1:0
    │
    └── fetch() buffered  ──► API Gateway (prod) ──► topic_visual Lambda
                                                          └── Bedrock: amazon.nova-canvas-v1:0
```

**AWS services used:**
- **Amazon Bedrock** — Claude Sonnet 4.5 global inference profile (text) + Nova Canvas (image)
- **AWS Lambda** — 8 functions (7 Flask streaming + 1 standard handler)
- **Amazon API Gateway** — REST API for image endpoint
- **Amazon S3** — Static website hosting
- **AWS SAM** — Infrastructure as code
- **GitHub Actions** — CI/CD pipeline

---

## 🚀 Pre-Deployment Checklist

Complete these steps **before** your first deploy.

### 1. Enable Bedrock Model Access

Go to: **AWS Console → Amazon Bedrock → Model Access → Manage model access**
Region: **ap-southeast-1 (Singapore)**

Enable both models:

| Model | Model ID |
|---|---|
| Claude Sonnet 4.5 | `global.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Nova Canvas | `amazon.nova-canvas-v1:0` |

> **Note:** Claude Sonnet 4.5 uses the **Global Cross-Region inference profile** — ap-southeast-1 is both a valid source and destination region. Nova Canvas is Amazon-native. Both should be available on most AWS accounts; if you hit an SCP block on Anthropic models, contact your org admin to allow `arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0`.

### 2. Create an S3 Bucket for SAM Artifacts

SAM needs an S3 bucket to stage Lambda deployment packages.

```bash
aws s3 mb s3://your-sam-deploy-bucket-name --region ap-southeast-1
```

Keep this bucket name — you'll add it as a GitHub secret.

### 3. Create an IAM User for GitHub Actions

Create an IAM user with programmatic access and attach this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "lambda:*",
        "apigateway:*",
        "iam:*",
        "bedrock:*"
      ],
      "Resource": "*"
    }
  ]
}
```

> For a tighter policy, scope each action to your specific resources. The wildcard policy above is suitable for initial setup.

### 4. Add GitHub Secrets

In your GitHub repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user access key ID |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret access key |
| `SAM_DEPLOY_BUCKET` | The S3 bucket name from step 2 |

---

## 📁 Project Structure

```
studysnap/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions CI/CD pipeline
├── frontend/
│   └── index.html              # Single-page app (all 11 widgets)
├── infra/
│   └── template.yaml           # AWS SAM infrastructure template
├── lambdas/
│   ├── estimated_study_time/   # Flask streaming Lambda
│   │   ├── app.py
│   │   ├── run.sh
│   │   └── requirements.txt
│   ├── bullet_point_summary/   # Flask streaming Lambda
│   ├── key_terms_glossary/     # Flask streaming Lambda
│   ├── real_world_examples/    # Flask streaming Lambda
│   ├── difficulty_level_tag/   # Flask streaming Lambda
│   ├── flashcards/             # Flask streaming Lambda
│   ├── interactive_quiz/       # Flask streaming chatbot Lambda
│   └── topic_visual/           # Standard Lambda (Nova Canvas image)
│       ├── app.py
│       └── requirements.txt
└── README.md
```

---

## 🔧 Local Development

### Prerequisites

- Python 3.12
- AWS SAM CLI (`pip install aws-sam-cli`)
- AWS CLI configured with `ap-southeast-1` credentials

### Run a Lambda locally

```bash
cd lambdas/bullet_point_summary
pip install -r requirements.txt
python app.py
# Flask runs on http://localhost:8080
```

Test with curl:

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"file_data": "<base64-pdf>", "file_mime": "application/pdf"}'
```

### SAM local invoke (image Lambda)

```bash
sam build --template infra/template.yaml
sam local invoke TopicVisualFunction \
  --event '{"httpMethod":"POST","body":"{\"topic_hint\":\"machine learning\"}"}'
```

---

## 🚢 Deployment

### Automatic (recommended)

Push to `main` — GitHub Actions handles everything:

1. SAM build + deploy to CloudFormation
2. Read all Lambda Function URLs from stack outputs
3. Inject URLs into `frontend/index.html` via `sed`
4. Upload frontend to S3 with `no-cache` headers
5. Print the live website URL

### Manual

```bash
# Build
sam build --template infra/template.yaml

# Deploy
sam deploy \
  --stack-name study-snap \
  --s3-bucket YOUR_SAM_DEPLOY_BUCKET \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region ap-southeast-1 \
  --no-confirm-changeset

# Get website URL
aws cloudformation describe-stacks \
  --stack-name study-snap \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteUrl'].OutputValue" \
  --output text
```

---

## 🎨 Dynamic Theme System

After generating study materials, the app analyses the output text and automatically switches the UI colour palette:

| Theme | Triggered by keywords |
|---|---|
| 💻 Tech | programming, algorithm, AI, python, database … |
| 🌿 Nature | biology, ecology, DNA, ecosystem, evolution … |
| 🎨 Art | design, painting, music, aesthetic, creative … |
| 🏛️ History | war, empire, revolution, dynasty, medieval … |
| 🔬 Science | chemistry, physics, quantum, calculus, molecule … |
| ✨ Default | (fallback — bright indigo/violet palette) |

---

## ⚙️ Configuration

All Bedrock models and region are set in `infra/template.yaml`. To change region:

1. Update `aws-region` in `.github/workflows/deploy.yml`
2. Update `region_name` in each `lambdas/*/app.py`
3. Update the IAM role ARNs in `infra/template.yaml`

---

## 🔒 Security Notes

- Lambda Function URLs use `AuthType: NONE` (public endpoints). For production, consider adding a CloudFront distribution with an API key or Cognito authentication.
- S3 bucket has public read access for static website hosting. The bucket contains only the frontend HTML — no secrets or user data.
- No user data is stored server-side. Session history is saved in the browser's `localStorage` only.

---

## 🐛 Troubleshooting

| Issue | Fix |
|---|---|
| `AccessDeniedException` from Bedrock | Your org SCP may be blocking third-party models. This app uses Amazon-native Nova Lite + Nova Canvas which should be permitted |
| `AWS::EarlyValidation` on SAM deploy | Ensure no `Cors` block inside `FunctionUrlConfig` |
| `samconfig.toml version` error | The template uses no samconfig.toml — pass all flags explicitly |
| Image generation fails | Enable `amazon.nova-canvas-v1:0` in Bedrock model access |
| Streaming stops mid-response | Increase Lambda `Timeout` in `template.yaml` (currently 60s) |
| CORS error in browser | Verify CORS headers are returned on both OPTIONS and POST routes |

---

## 📜 License

MIT — free to use, modify, and deploy.
