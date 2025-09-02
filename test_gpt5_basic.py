#!/usr/bin/env python3
"""
Test basic GPT-5 functionality
"""

import asyncio
import json
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_gpt5():
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("Testing GPT-5 basic functionality...")
    print(f"API Key: {os.getenv('OPENAI_API_KEY')[:20]}...")
    
    try:
        # Test basic text generation
        print("\n1. Testing basic text generation...")
        response = await client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "user", "content": "Say hello and tell me you are GPT-5"}
            ],
            max_completion_tokens=50
        )
        print(f"✅ Response: {response.choices[0].message.content}")
        print(f"Tokens: {response.usage.total_tokens}")
        
        # Test JSON mode
        print("\n2. Testing JSON mode...")
        response = await client.chat.completions.create(
            model="gpt-5", 
            messages=[
                {"role": "user", "content": 'Return JSON: {"message": "hello from GPT-5", "status": "working"}'}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=100
        )
        
        content = response.choices[0].message.content
        print(f"Raw content: '{content}'")
        
        if content and content.strip():
            result = json.loads(content)
            print(f"✅ JSON Response: {result}")
        else:
            print("❌ Empty response in JSON mode")
            
        # Test other models
        print("\n3. Testing other models...")
        for model in ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"]:
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": f"Say hello from {model}"}],
                    max_tokens=20
                )
                print(f"✅ {model}: {response.choices[0].message.content}")
            except Exception as e:
                print(f"❌ {model}: {str(e)[:50]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    asyncio.run(test_gpt5())