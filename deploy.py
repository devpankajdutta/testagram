import boto3
import shutil
import os
import subprocess
import time

# Config
AWS_REGION = "us-east-1"
AWS_ENDPOINT_URL = "http://localhost:4566"
LAMBDA_FUNCTION_NAME = "testagram-api"
ROLE_NAME = "lambda-ex-role"
ZIP_FILE = "function.zip"
RUNTIME = "python3.11"
HANDLER = "handler.handler"

def create_zip():
    print("Creating deployment package...")
    # 1. Copy app to a temporary build dir
    if os.path.exists("build"):
        shutil.rmtree("build")
    os.makedirs("build")
    
    # 2. Copy App Code
    shutil.copytree("app", "build/app")
    shutil.copy("handler.py", "build/handler.py") # Add handler at root
    
    # 3. Install deps to build dir (Target)
    # 3. Install deps to build dir (Target)
    # We need Linux wheels for Lambda (running in Docker/LocalStack)
    # Using --platform manylinux2014_x86_64 to get linux binaries
    cmd = [
        "pip", "install", 
        "-r", "requirements.txt", 
        "--target", "build", 
        "--platform", "manylinux2014_x86_64",
        "--only-binary=:all:", 
        "--implementation", "cp",
        "--python-version", "3.11", 
        "--abi", "cp311",
        "--upgrade"
    ]
    subprocess.check_call(cmd)
    
    # 4. Zip it
    shutil.make_archive("function", "zip", "build")
    print(f"Created {ZIP_FILE}")

def deploy():
    session = boto3.Session(aws_access_key_id="test", aws_secret_access_key="test", region_name=AWS_REGION)
    lambda_client = session.client("lambda", endpoint_url=AWS_ENDPOINT_URL)
    iam = session.client("iam", endpoint_url=AWS_ENDPOINT_URL)
    apigateway = session.client("apigatewayv2", endpoint_url=AWS_ENDPOINT_URL)

    # 1. Create Role
    try:
        iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument='{"Version": "2012-10-17","Statement": [{"Effect": "Allow","Principal": {"Service": "lambda.amazonaws.com"},"Action": "sts:AssumeRole"}]}'
        )
        print(f"Role {ROLE_NAME} created.")
    except Exception as e:
        print(f"Role creation skipped (might exist): {e}")

    # 2. Update/Create Lambda
    with open(ZIP_FILE, "rb") as f:
        zipped_code = f.read()

    # Always delete first to avoid update issues
    try:
        lambda_client.delete_function(FunctionName=LAMBDA_FUNCTION_NAME)
        print(f"Deleted existing function {LAMBDA_FUNCTION_NAME}")
    except Exception:
        pass

    try:
        lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime=RUNTIME,
            Role=f"arn:aws:iam::000000000000:role/{ROLE_NAME}",
            Handler=HANDLER,
            Code={"ZipFile": zipped_code},
            Environment={
                "Variables": {
                    "BUCKET_NAME": "testagram-images",
                    "TABLE_NAME": "testagram-metadata",
                    "ENV": "dev"
                }
            },
            Timeout=30,
            MemorySize=128
        )
        print(f"Lambda {LAMBDA_FUNCTION_NAME} created.")
    except Exception as e:
        print(f"Error creating lambda: {e}")
        # traceback.print_exc()

    # 3. Create API Gateway (REST API V1) which is more robust on LocalStack
    print("Checking API Gateway (V1)...")
    apigateway = session.client("apigateway", endpoint_url=AWS_ENDPOINT_URL)
    
    try:
        apis = apigateway.get_rest_apis()
    except Exception as e:
        print(f"Failed to get_rest_apis: {e}")
        raise

    api_id = None
    for item in apis.get("items", []):
        if item["name"] == "TestagramGateway":
            api_id = item["id"]
            break
            
    if not api_id:
        print("Creating REST API...")
        try:
            api_res = apigateway.create_rest_api(name="testagram-api")
            api_id = api_res["id"]
        except Exception as e:
            print(f"Failed to create_rest_api: {e}")
            raise
        
    print(f"API ID: {api_id}")

    # 4. Integrate with Lambda
    # Get Root Resource
    resources = apigateway.get_resources(restApiId=api_id)
    root_id = None
    for item in resources.get("items", []):
        if item["path"] == "/":
            root_id = item["id"]
            break

    # We want a proxy resource catch-all: /{proxy+}
    # 1. Create Resource /{proxy+}
    proxy_id = None
    # Check if exists
    for item in resources.get("items", []):
        if item.get("pathPart") == "{proxy+}":
            proxy_id = item["id"]
            break
            
    if not proxy_id:
        print("Creating Proxy Resource...")
        resp = apigateway.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart="{proxy+}"
        )
        proxy_id = resp["id"]

    # 2. Put Method ANY
    print("Configuring ANY Method...")
    apigateway.put_method(
        restApiId=api_id,
        resourceId=proxy_id,
        httpMethod="ANY",
        authorizationType="NONE"
    )

    # 3. Put Integration
    print("Configuring Integration...")
    # Note: LocalStack requires proper formatting for URI
    # uri = f"arn:aws:apigateway:{AWS_REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
    # But for LocalStack simpler uri might work or we use the arn constructed before
    lambda_arn = f"arn:aws:lambda:{AWS_REGION}:000000000000:function:{LAMBDA_FUNCTION_NAME}"
    uri = f"arn:aws:apigateway:{AWS_REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

    apigateway.put_integration(
        restApiId=api_id,
        resourceId=proxy_id,
        httpMethod="ANY",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=uri
    )

    # 4. Deploy
    print("Deploying API...")
    apigateway.create_deployment(
        restApiId=api_id,
        stageName="dev"
    )

    # 5. Update Lambda with ROOT_PATH for Swagger support
    print(f"Updating Lambda {LAMBDA_FUNCTION_NAME} with ROOT_PATH...")
    root_path = f"/restapis/{api_id}/dev/_user_request_"
    lambda_client.update_function_configuration(
        FunctionName=LAMBDA_FUNCTION_NAME,
        Environment={
            "Variables": {
                "BUCKET_NAME": "testagram-images",
                "TABLE_NAME": "testagram-metadata",
                "ENV": "dev",
                "ROOT_PATH": root_path
            }
        }
    )
        
    print(f"Deployment Complete!")
    print(f"Endpoint: http://localhost:4566/restapis/{api_id}/dev/_user_request_/")

    with open("api_id.txt", "w") as f:
        f.write(api_id)
        
    print(f"Deployment Complete!")
    print(f"Endpoint: http://localhost:4566/restapis/{api_id}/test/_user_request_ (Mock URL) or http://localhost:4566/_aws/execute-api/{api_id}/$default")
    # Using LocalStack's new endpoint format often simplifies to:
    print(f"Try: http://{api_id}.execute-api.localhost.localstack.cloud:4566/")

import traceback

if __name__ == "__main__":
    try:
        # Check if zip exists, if not create it
        if not os.path.exists(ZIP_FILE):
             create_zip()
        deploy()
    except Exception:
        traceback.print_exc()
