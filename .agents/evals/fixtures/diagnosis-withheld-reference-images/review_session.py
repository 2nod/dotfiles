class ReviewSession:
    def __init__(self, originals, references):
        self.originals = list(originals)
        self.references = list(references)
        self.recorded = False

    def begin(self):
        return {"images": self.originals + self.references, "reference_text": None}

    def inspect(self, image_id):
        for image in self.originals + self.references:
            if image["id"] == image_id:
                return image
        raise KeyError(image_id)

    def record_observations(self, observations):
        if set(observations) != {image["id"] for image in self.originals}:
            raise ValueError("Incomplete original observations")
        self.recorded = True
        return {"images": self.references, "reference_text": "retained label"}
