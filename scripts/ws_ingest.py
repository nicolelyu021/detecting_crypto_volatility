import asyncio, time, orjson
from kafka import KafkaProducer
import websockets

# helper
def b(s): return s.encode("utf-8")

async def subscribe(ws, pair):
    # correct Coinbase message format
    msg = {
        "type": "subscribe",
        "channels": [{"name": "ticker", "product_ids": [pair]}]
    }
    await ws.send(orjson.dumps(msg).decode())

async def run(pair="BTC-USD", minutes=10, ws_url="wss://ws-feed.exchange.coinbase.com",
              topic="ticks.raw", servers=None, heartbeat=25, backoff=5):
    # Use environment variable if servers not provided, fallback to localhost
    import os
    if servers is None:
        servers = os.getenv("KAFKA_SERVERS", "localhost:9092")
    p = KafkaProducer(bootstrap_servers=servers,
                      value_serializer=lambda v: orjson.dumps(v))
    deadline = time.time() + minutes * 60
    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=heartbeat) as ws:
                await subscribe(ws, pair)
                while True:
                    raw = await ws.recv()
                    t = time.time()
                    rec = {"ts": t, "pair": pair, "raw": raw}
                    
                    # Send to Kafka
                    p.send(topic, value=rec)
                    
                    # Also save to file for replay
                    from pathlib import Path
                    raw_dir = Path("data/raw"); raw_dir.mkdir(parents=True, exist_ok=True)
                    with open(raw_dir / "slice.ndjson", "ab") as f:
                        f.write(orjson.dumps(rec) + b"\n")

                    if time.time() > deadline:
                        print("Finished ingest run")
                        p.flush()  # Ensure all messages are sent
                        return
        except Exception as e:
            print("Connection error:", e)
            await asyncio.sleep(backoff)

if __name__ == "__main__":
    asyncio.run(run())
