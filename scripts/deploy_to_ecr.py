#!/usr/bin/env python3
"""
Deployment script for pushing Docker images to AWS ECR.

This script automates the process of:
1. Building the Docker image
2. Authenticating with AWS ECR
3. Tagging the image appropriately
4. Pushing the image to ECR
"""

import os
import subprocess
import sys
import boto3
from botocore.exceptions import ClientError

def run_command(command, cwd=None):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)

def get_aws_account_id():
    """Get AWS account ID using boto3."""
    try:
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
        return account_id
    except ClientError as e:
        print(f"Error getting AWS account ID: {e}")
        return None

def main():
    # Get configuration from environment variables
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    ecr_repository_uri = os.getenv('ECR_REPOSITORY_URI')
    image_tag = os.getenv('IMAGE_TAG', 'latest')

    if not ecr_repository_uri:
        print("ECR_REPOSITORY_URI environment variable is required")
        print("Example: export ECR_REPOSITORY_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo")
        sys.exit(1)

    # Parse repository URI to get account ID and repository name
    try:
        account_id = ecr_repository_uri.split('.')[0]
        repo_name = ecr_repository_uri.split('/')[-1]
    except IndexError:
        print("Invalid ECR repository URI format")
        sys.exit(1)

    print(f"Deploying to AWS ECR...")
    print(f"Repository: {ecr_repository_uri}")
    print(f"Tag: {image_tag}")
    print(f"Region: {aws_region}")

    # Login to ECR
    print("Logging in to Amazon ECR...")
    login_cmd = f"aws ecr get-login-password --region {aws_region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{aws_region}.amazonaws.com"
    run_command(login_cmd)

    # Build the Docker image
    print("Building Docker image...")
    build_cmd = f"docker build -f docker/Dockerfile -t {ecr_repository_uri}:{image_tag} ."
    run_command(build_cmd)

    # Tag as latest if not already
    if image_tag != 'latest':
        print("Tagging image as latest...")
        tag_cmd = f"docker tag {ecr_repository_uri}:{image_tag} {ecr_repository_uri}:latest"
        run_command(tag_cmd)

    # Push the image
    print("Pushing image to ECR...")
    push_cmd = f"docker push {ecr_repository_uri}:{image_tag}"
    run_command(push_cmd)

    # Push latest tag if different
    if image_tag != 'latest':
        push_latest_cmd = f"docker push {ecr_repository_uri}:latest"
        run_command(push_latest_cmd)

    print("Deployment complete!")
    print(f"Image URI: {ecr_repository_uri}:{image_tag}")

if __name__ == '__main__':
    main()