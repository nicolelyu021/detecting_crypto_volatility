import argparse, time
from kafka import KafkaConsumer

ap = argparse.ArgumentParser()
ap.add_argument("--topic", default="ticks.raw")
ap.add_argument("--min", type=int, default=100)
ap.add_argument("--servers", default="localhost:9092")
args = ap.parse_args()

c = KafkaConsumer(
    args.topic,
    bootstrap_servers=args.servers,
    auto_offset_reset="earliest",   # start at beginning if no committed offset
    group_id="sanity-check-1",      # new group so there is no prior offset
    enable_auto_commit=False,
    consumer_timeout_ms=10000
)

count = 0
start = time.time()
for _ in c:
    count += 1
    if count >= args.min:
        break

print(f"messages_seen={count} seconds={(time.time()-start):.1f}")
