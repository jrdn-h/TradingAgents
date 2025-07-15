import tempfile
import os
import asyncio
from datetime import datetime
from tradingagents.sources.tweet_source import CSVReplaySource, Tweet

def test_csv_replay_source_contract():
    # Create a tiny CSV with 3 rows
    rows = [
        {"id": "1", "created_at": "2024-01-01T00:00:01", "author": "alice", "text": "hello world"},
        {"id": "2", "created_at": "2024-01-01T00:00:02", "author": "bob", "text": "gm"},
        {"id": "3", "created_at": "2024-01-01T00:00:03", "author": "carol", "text": "moon"},
    ]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, newline='', encoding='utf-8') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=["id", "created_at", "author", "text"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        csv_path = f.name
    try:
        source = CSVReplaySource(csv_path)
        async def run():
            tweets = []
            async for tweet in source.stream():
                assert isinstance(tweet, Tweet)
                tweets.append(tweet)
            assert len(tweets) == 3
            # Check order
            assert [t.id for t in tweets] == ["1", "2", "3"]
            assert [t.author for t in tweets] == ["alice", "bob", "carol"]
            assert [t.text for t in tweets] == ["hello world", "gm", "moon"]
            assert [t.created_at for t in tweets] == [
                datetime.fromisoformat(r["created_at"]) for r in rows
            ]
        asyncio.run(run())
    finally:
        os.remove(csv_path) 