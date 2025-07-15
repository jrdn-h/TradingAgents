#!/usr/bin/env python3
"""
Quick sanity check for TwikitSource.
"""

import os
import asyncio
from dotenv import load_dotenv
from tradingagents.sources.tweet_source import TwikitSource

# Load environment variables from .env file
load_dotenv()

async def test_twikit():
    print("🧪 Testing TwikitSource...")
    
    # Check environment variables
    username = os.environ.get("TWIKIT_USERNAME")
    password = os.environ.get("TWIKIT_PASSWORD")
    
    if not username or not password:
        print("❌ Set TWIKIT_USERNAME and TWIKIT_PASSWORD environment variables")
        print("Example:")
        print("  export TWIKIT_USERNAME='your-username'")
        print("  export TWIKIT_PASSWORD='your-password'")
        return
    
    print(f"✅ Found credentials for: {username}")
    
    try:
        source = TwikitSource(filters=["BTC", "ETH"])
        print("✅ TwikitSource initialized")
        
        count = 0
        async for tweet in source.stream():
            print(f"📱 {tweet.created_at} @{tweet.author}: {tweet.text[:80]}...")
            count += 1
            if count >= 3:
                print("✅ TwikitSource test successful!")
                break
                
        print("✅ TwikitSource test successful!")
        
    except Exception as e:
        print(f"❌ TwikitSource error: {e}")

if __name__ == "__main__":
    asyncio.run(test_twikit()) 