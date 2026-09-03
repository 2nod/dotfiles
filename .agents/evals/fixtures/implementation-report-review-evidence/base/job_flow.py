def create_job(store, translation_id, request):
    remote_job = store.request(request)
    return store.save_job(translation_id, remote_job.id)


def handle_success(store, job, result, context):
    inference = store.create_inference(job.translation_id, result)
    store.mark_success(job.id, inference.id, result, context)
    store.publish_context(job.translation_id, context)
