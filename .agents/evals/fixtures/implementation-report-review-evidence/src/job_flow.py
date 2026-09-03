def create_rerun_job(store, translation_id, target_item, request):
    with store.transaction() as tx:
        with tx.lock_translation(translation_id):
            active = tx.find_active_job(translation_id)
            if active and active.target_item == target_item:
                return active
            if active:
                raise RuntimeError("another rerun is active")
            return tx.create_job(translation_id, target_item, request)


def handle_success(
    store,
    job,
    result,
    context,
    current_revision_id,
    expected_revision_id,
    existing_success=None,
):
    if current_revision_id != expected_revision_id:
        raise RuntimeError("revision changed")
    if existing_success is not None:
        store.repair_missing_artifacts(job.id, result, context)
        return existing_success.inference_id
    store.validate_exact_output_ids(job.target_item, result)
    inference = store.apply_target_item(job.target_item, result)
    store.mark_success(job.id, inference.id, result, context)
    if job.target_item is None:
        store.publish_context(job.translation_id, context)
    return inference.id
