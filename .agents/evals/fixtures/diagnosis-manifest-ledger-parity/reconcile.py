def reconcile(manifest, ledger, receipt=None):
    if receipt and receipt.get("valid"):
        return {"status": "reconciled", "lifecycle": "reconciled"}
    return {"status": "fresh", "lifecycle": manifest["lifecycle"]}
