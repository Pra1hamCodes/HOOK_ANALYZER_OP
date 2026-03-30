from ingestion import ingest_video
import json

result = ingest_video('your_video.mp4')

print(json.dumps({
    **result,
    # shorten frame lists for readability
    'baseline_frames': f"{len(result['baseline_frames'])} frames",
    'burst_frames':    {k: f"{len(v)} frames" for k, v in result['burst_frames'].items()}
}, indent=2))