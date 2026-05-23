# Docker Deployment and AWS ECR Configuration

This document explains how to build and deploy the Multi-Agent RAG Platform using Docker and AWS ECR.

## Prerequisites

1. Docker and Docker Compose installed
2. AWS CLI configured with appropriate permissions
3. An AWS ECR repository created

## Building the Docker Image

The Docker image is automatically built and pushed to AWS ECR when code is pushed to the `main` branch, thanks to our GitHub Actions workflow.

To build locally:
```bash
docker build -f docker/Dockerfile -t multi-rag-platform .
```

## AWS ECR Setup

1. Create an ECR repository in your AWS account:
   ```bash
   aws ecr create-repository --repository-name multi-rag-platform
   ```

2. Note the repository URI returned by the command.

## GitHub Secrets Configuration

Configure the following secrets in your GitHub repository:

| Secret Name | Description |
|-------------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key with ECR permissions |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key |
| `ECR_REPOSITORY_URI` | Full URI of your ECR repository |

Additional secrets for application functionality:

| Secret Name | Description |
|-------------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `COHERE_API_KEY` | Cohere API key |
| `QDRANT_URL` | Qdrant Cloud URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |

## Production Deployment

1. Pull the latest image from ECR:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
   docker pull YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/multi-rag-platform:latest
   ```

2. Create a `.env.prod` file with your production environment variables.

3. Deploy using Docker Compose:
   ```bash
   docker-compose -f docker/docker-compose.prod.yml --env-file .env.prod up -d
   ```

## Environment Configuration

Environment variables are configured in three places:

1. **Development**: `.env` file in the project root
2. **Production**: `.env.prod` file (not in version control)
3. **Docker Builds**: Passed via Docker Compose or Docker run commands

See `core/config.py` for all configurable settings.