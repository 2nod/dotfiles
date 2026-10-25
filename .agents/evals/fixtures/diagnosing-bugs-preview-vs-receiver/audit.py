def summarize(probe):
    image = any(block["type"] == "image" for block in probe["preview_content"])
    return {
        "call_completed": probe["status"] == "completed",
        "server_sent_image": image,
        "visual_receipt": "verified" if image else "no_image",
    }
