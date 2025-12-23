#!/usr/bin/env python3
"""
Test script to diagnose nano banana pro model behavior.
Tests both generation time and response format.
"""
import asyncio
import os
import sys
import time
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv('.env.local')

from imagine.services.fal import FalService

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_nano_banana():
    """Test nano banana pro model with a simple prompt."""
    fal_service = FalService()
    
    prompt = "a blue bird"
    model = "fal-ai/nano-banana-pro"
    
    print(f"\n{'='*60}")
    print(f"Testing model: {model}")
    print(f"Prompt: {prompt}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    try:
        logger.info("Starting generation...")
        image_data = await fal_service.generate_image(prompt, model)
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"SUCCESS!")
        print(f"{'='*60}")
        print(f"Generation time: {elapsed:.2f} seconds")
        print(f"Image data size: {len(image_data)} bytes ({len(image_data)/1024:.1f} KB)")
        print(f"Data type: {type(image_data)}")
        print(f"First 20 bytes (hex): {image_data[:20].hex()}")
        
        # Check if it's a valid image
        if image_data[:8] == b'\x89PNG\r\n\x1a\n':
            print("Format: PNG")
        elif image_data[:2] == b'\xff\xd8':
            print("Format: JPEG")
        elif image_data[:4] == b'RIFF':
            print("Format: WebP")
        else:
            print(f"Format: Unknown (magic bytes: {image_data[:8]})")
        
        # Save test image
        output_path = "/tmp/test_nano_banana_bluebird.png"
        with open(output_path, "wb") as f:
            f.write(image_data)
        print(f"Image saved to: {output_path}")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"FAILED after {elapsed:.2f} seconds")
        print(f"{'='*60}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        logger.exception("Full traceback:")
        

async def test_comparison():
    """Compare nano banana with fast-sdxl for reference."""
    fal_service = FalService()
    prompt = "a blue bird"
    
    models = [
        "fal-ai/fast-sdxl",
        "fal-ai/nano-banana-pro",
    ]
    
    print(f"\n{'='*60}")
    print("COMPARISON TEST")
    print(f"{'='*60}\n")
    
    for model in models:
        print(f"\nTesting: {model}")
        print("-" * 40)
        
        start_time = time.time()
        try:
            image_data = await fal_service.generate_image(prompt, model)
            elapsed = time.time() - start_time
            print(f"  Status: SUCCESS")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Size: {len(image_data)/1024:.1f} KB")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  Status: FAILED")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Error: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test nano banana pro model")
    parser.add_argument("--compare", action="store_true", help="Compare with fast-sdxl")
    args = parser.parse_args()
    
    if args.compare:
        asyncio.run(test_comparison())
    else:
        asyncio.run(test_nano_banana())
