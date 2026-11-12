import json
import os
import time
import boto3
from botocore.exceptions import ClientError

def handler(event, context):
    table = boto3.resource("dynamodb").Table(os.environ["DELIVERY_TABLE"])
    failed = []
    for record in event.get("Records", []):
        try:
            envelope = json.loads(record["body"])
            message = json.loads(envelope["Message"])
            event_id = message["eventId"]
            table.put_item(Item={"pk":"DELIVERY#"+event_id,"processedAt":int(time.time()),
                                 "expiresAt":int(time.time())+2592000},
                           ConditionExpression="attribute_not_exists(pk)")
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                failed.append({"itemIdentifier":record["messageId"]})
        except (ValueError, KeyError, TypeError):
            failed.append({"itemIdentifier":record["messageId"]})
    return {"batchItemFailures":failed}
