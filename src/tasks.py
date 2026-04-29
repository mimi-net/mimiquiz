import json
import uuid

from celery.exceptions import TimeoutError
from celery.result import AsyncResult, allow_join_result

from celery_app import EXCHANGE_TYPE, SEND_NETWORK_EXCHANGE, app


def create_emulation_task(net_schema):
    if not net_schema.get("jobs"):
        return []

    net_schema = (
        json.dumps(net_schema) if not isinstance(net_schema, str) else net_schema
    )

    async_obj = app.send_task(
        "tasks.mininet_worker",
        [net_schema],
        routing_key=str(uuid.uuid4()),
        exchange=SEND_NETWORK_EXCHANGE,
        exchange_type=EXCHANGE_TYPE,
    )

    async_res = AsyncResult(id=async_obj.id, app=app)

    try:
        with allow_join_result():
            animation, _ = async_res.wait(timeout=120)

            return animation
    except TimeoutError:
        # TODO improve error message (add user info)
        raise Exception(f"""Check task failed!\nNetwork Schema: {net_schema}.""")
