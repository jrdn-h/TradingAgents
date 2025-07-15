import os
import asyncio
import pytest
from tradingagents.sources.tweet_source import TwikitSource, Tweet

pytestmark = pytest.mark.external

@pytest.mark.skipif(
    not os.environ.get("TWIKIT_E2E"),
    reason="Set TWIKIT_E2E=1 to run Twikit live tests."
)
def test_twikit_source_smoke():
    username = os.environ.get("TWIKIT_USER", "stubuser")
    email = os.environ.get("TWIKIT_EMAIL", "stub@example.com")
    password = os.environ.get("TWIKIT_PASS", "stubpass")
    source = TwikitSource(username, email, password, query="bitcoin")

    async def run():
        tweets = []
        async for tweet in source.stream():
            assert isinstance(tweet, Tweet)
            tweets.append(tweet)
            if len(tweets) >= 5:
                break
        assert len(tweets) == 5
    asyncio.run(run()) 