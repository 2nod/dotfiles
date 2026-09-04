def test_reuses_same_active_rerun(store, request):
    active = store.active_job(target_item=4)

    result = create_rerun_job(store, "translation-1", 4, request)

    assert result.id == active.id
    assert store.created_jobs == []


def test_rejects_different_active_rerun(store, request):
    store.active_job(target_item=8)

    with raises(RuntimeError, match="another rerun is active"):
        create_rerun_job(store, "translation-1", 4, request)

    assert store.created_jobs == []


def test_rejects_changed_revision_without_apply(store, job, result, context):
    store.current_revision_id = "revision-2"

    with raises(RuntimeError, match="revision changed"):
        handle_success(
            store,
            job,
            result,
            context,
            current_revision_id="revision-2",
            expected_revision_id="revision-1",
        )

    assert store.applied_items == []
    assert store.successful_jobs == []
