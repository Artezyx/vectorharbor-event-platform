import json
import os
import uuid
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from .domain import normalize, digest, identity, key, result

def handler(event, context):
    try:
        tenant = identity(event)
        unique = key(event.get("headers"))
        payload = normalize(json.loads(event.get("body") or "{}"))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return result(400, {"error": str(exc)})
    table = boto3.resource("dynamodb").Table(os.environ["EVENTS_TABLE"])
    pk = "TENANT#" + tenant
    sk = "KEY#" + unique
    item = {"pk":pk, "sk":sk, "eventId":str(uuid.uuid4()), "data":payload,
            "fingerprint":digest(payload), "createdAt":datetime.now(timezone.utc).isoformat()}
    try:
        table.put_item(Item=item, ConditionExpression="attribute_not_exists(pk)")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        old = table.get_item(Key={"pk":pk,"sk":sk}, ConsistentRead=True).get("Item")
        if not old:
            return result(503, {"error":"please retry"})
        if old["fingerprint"] != item["fingerprint"]:
            return result(409, {"error":"conflicting replay"})
        return result(200, {"eventId":old["eventId"],"replayed":True})
    try:
        boto3.client("sns").publish(TopicArn=os.environ["EVENT_TOPIC"], Message=json.dumps({
            "eventId":item["eventId"],"tenant":tenant,"data":payload}))
    except ClientError:
        return result(503, {"error":"event recorded but notification pending","eventId":item["eventId"]})
    return result(202, {"eventId":item["eventId"],"replayed":False})
