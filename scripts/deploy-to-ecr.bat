@echo off
REM deploy-to-ecr.bat
REM Script to manually build and deploy Docker image to AWS ECR on Windows

REM Check if AWS CLI is installed
where aws >nul 2>&1
if %errorlevel% neq 0 (
    echo AWS CLI is not installed. Please install it first.
    exit /b 1
)

REM Check if Docker is installed
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker is not installed. Please install it first.
    exit /b 1
)

REM Default values - update these as needed
if "%AWS_DEFAULT_REGION%"=="" set AWS_DEFAULT_REGION=us-east-1
if "%ECR_REPOSITORY_URI%"=="" set ECR_REPOSITORY_URI=
if "%IMAGE_TAG%"=="" set IMAGE_TAG=manual-%date:~10,4%%date:~4,2%%date:~7,2%-%time:~0,2%%time:~3,2%%time:~6,2%

REM Remove spaces from timestamp
set IMAGE_TAG=%IMAGE_TAG: =0%

REM Check if ECR repository URI is provided
if "%ECR_REPOSITORY_URI%"=="" (
    echo Please set ECR_REPOSITORY_URI environment variable
    echo Example: set ECR_REPOSITORY_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo
    exit /b 1
)

echo Building and deploying to ECR...
echo Repository: %ECR_REPOSITORY_URI%
echo Tag: %IMAGE_TAG%
echo Region: %AWS_DEFAULT_REGION%

REM Get AWS account ID from ECR URI
for /f "tokens=1 delims=." %%a in ("%ECR_REPOSITORY_URI%") do set ACCOUNT_ID=%%a
for /f "tokens=2 delims=/" %%a in ("%ECR_REPOSITORY_URI%") do set REPO_NAME=%%a

REM Login to ECR
echo Logging in to Amazon ECR...
aws ecr get-login-password --region %AWS_DEFAULT_REGION% | docker login --username AWS --password-stdin %ACCOUNT_ID%.dkr.ecr.%AWS_DEFAULT_REGION%.amazonaws.com

REM Build the Docker image
echo Building Docker image...
docker build -f docker/Dockerfile -t %ECR_REPOSITORY_URI%:%IMAGE_TAG% .

REM Tag the image as latest
echo Tagging image as latest...
docker tag %ECR_REPOSITORY_URI%:%IMAGE_TAG% %ECR_REPOSITORY_URI%:latest

REM Push the image
echo Pushing image to ECR...
docker push %ECR_REPOSITORY_URI%:%IMAGE_TAG%
docker push %ECR_REPOSITORY_URI%:latest

echo Deployment complete!
echo Image URI: %ECR_REPOSITORY_URI%:%IMAGE_TAG%