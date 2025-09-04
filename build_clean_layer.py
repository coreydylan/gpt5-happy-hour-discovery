#!/usr/bin/env python3
"""
Clean Lambda layer builder using Docker for x86_64 compatibility
"""
import subprocess
import os
import shutil
import zipfile
from pathlib import Path

def create_dockerfile():
    dockerfile_content = """
FROM public.ecr.aws/lambda/python:3.11-x86_64

RUN pip install --target /opt/python openai==1.99.1 supabase==2.9.1

# Clean up any unnecessary files
RUN find /opt/python -name "*.pyc" -delete
RUN find /opt/python -name "__pycache__" -exec rm -rf {} + || true
RUN find /opt/python -name "*.so" -exec strip {} + || true

CMD ["echo", "Layer built successfully"]
"""
    
    with open('Dockerfile.layer', 'w') as f:
        f.write(dockerfile_content)

def build_layer():
    print("Creating clean Dockerfile...")
    create_dockerfile()
    
    print("Building Docker image for x86_64...")
    subprocess.run([
        'docker', 'build', 
        '--platform', 'linux/amd64',
        '-f', 'Dockerfile.layer',
        '-t', 'gpt5-layer-builder', 
        '.'
    ], check=True)
    
    print("Extracting dependencies from Docker container...")
    container_id = subprocess.run([
        'docker', 'create', 'gpt5-layer-builder'
    ], capture_output=True, text=True, check=True).stdout.strip()
    
    # Clean up previous builds
    if os.path.exists('python'):
        shutil.rmtree('python')
    
    subprocess.run([
        'docker', 'cp', f'{container_id}:/opt/python', '.'
    ], check=True)
    
    subprocess.run(['docker', 'rm', container_id], check=True)
    
    print("Creating layer ZIP...")
    if os.path.exists('gpt5-layer-clean.zip'):
        os.remove('gpt5-layer-clean.zip')
    
    with zipfile.ZipFile('gpt5-layer-clean.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('python'):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = file_path
                zipf.write(file_path, arc_name)
    
    print("Uploading layer to AWS...")
    result = subprocess.run([
        'aws', 'lambda', 'publish-layer-version',
        '--layer-name', 'gpt5-dependencies-clean',
        '--zip-file', 'fileb://gpt5-layer-clean.zip',
        '--compatible-runtimes', 'python3.11',
        '--compatible-architectures', 'x86_64',
        '--description', 'Clean GPT-5 dependencies built with Docker'
    ], capture_output=True, text=True, check=True)
    
    import json
    layer_info = json.loads(result.stdout)
    layer_version = layer_info['Version']
    layer_arn = layer_info['LayerVersionArn']
    
    print(f"Layer version {layer_version} created: {layer_arn}")
    
    print("Updating Lambda function...")
    subprocess.run([
        'aws', 'lambda', 'update-function-configuration',
        '--function-name', 'gpt5-happy-hour-orchestrator-dev',
        '--layers', layer_arn
    ], check=True)
    
    print("Waiting for function update...")
    subprocess.run([
        'aws', 'lambda', 'wait', 'function-updated',
        '--function-name', 'gpt5-happy-hour-orchestrator-dev'
    ], check=True)
    
    print(f"✅ Clean layer deployed successfully! Version: {layer_version}")
    
    # Clean up
    shutil.rmtree('python')
    os.remove('Dockerfile.layer')
    os.remove('gpt5-layer-clean.zip')

if __name__ == "__main__":
    build_layer()