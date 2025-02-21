import collections, time, typing, pytz, boto3
from  multiprocessing import Process
from datetime import datetime

from src.helpers.graceful_killer import GracefulKiller

# from helpers import GracefulKiller, syncSecretFromDDB
# from helpers import UPDATING_SECRETS, WAIT_TIME, STREAM_ARN



Shard = collections.namedtuple(
    typename="Shard",
    field_names=[
        "stream_arn",
        "shard_id",
        "parent_shard_id",
        "starting_sequence_number",
        "ending_sequence_number"
    ]
)


def list_all_shards(stream_arn: str, **kwargs: dict) -> typing.List[Shard]:
    
    def _shard_response_to_shard(response: dict) -> Shard:
        return Shard(
            stream_arn=stream_arn,
            shard_id=response.get("ShardId"),
            parent_shard_id=response.get("ParentShardId"),
            starting_sequence_number=response.get(
                "SequenceNumberRange", {}).get("StartingSequenceNumber"),
            ending_sequence_number=response.get(
                "SequenceNumberRange", {}).get("EndingSequenceNumber")
        )
    client = boto3.client("dynamodbstreams")
    pagination_args = {}
    exclusive_start_shard_id = kwargs.get("next_page_identifier", None)
    if exclusive_start_shard_id is not None:
        pagination_args["ExclusiveStartShardId"] = exclusive_start_shard_id
    response = client.describe_stream(
        StreamArn=stream_arn,
        **pagination_args
    )
    list_of_shards = [_shard_response_to_shard(item) for item in response["StreamDescription"]["Shards"]]
    next_page_identifier = response["StreamDescription"].get("LastEvaluatedShardId")
    if next_page_identifier is not None:
        list_of_shards += list_all_shards(
            stream_arn=stream_arn,
            next_page_identifier=next_page_identifier
        )
    return list_of_shards


def is_open_shard(shard: Shard) -> bool:
    return shard.ending_sequence_number is None


def list_open_shards(stream_arn: str) -> typing.List[Shard]:
    all_shards = list_all_shards(
        stream_arn=stream_arn
    )
    open_shards = [shard for shard in all_shards if is_open_shard(shard)]
    return open_shards


def get_shard_iterator(shard: Shard, iterator_type: str = "LATEST") -> str:
    client = boto3.client("dynamodbstreams")
    response = client.get_shard_iterator(
        StreamArn=shard.stream_arn,
        ShardId=shard.shard_id,
        ShardIteratorType=iterator_type
    )    
    return response["ShardIterator"]


def get_next_records(shard_iterator: str) -> typing.Tuple[typing.List[dict], str]:
    client = boto3.client("dynamodbstreams")
    response = client.get_records(ShardIterator=shard_iterator)
    return response["Records"], response.get("NextShardIterator")


def shard_watcher(shard: Shard, callables: typing.List[typing.Callable], 
      start_at_oldest = False, updating_secrets = UPDATING_SECRETS):
    shard_iterator_type = "TRIM_HORIZON" if start_at_oldest else "LATEST"
    shard_iterator = get_shard_iterator(shard, shard_iterator_type)
    while shard_iterator is not None:
        records, shard_iterator = get_next_records(shard_iterator)
        for record in records:
            for handler in callables:
                handler(record)
                if updating_secrets.value:
                    updating_secrets.value = 0
                    time.sleep(WAIT_TIME)
                    syncSecretFromDDB(updating_secrets)
        time.sleep(0.5)


def start_watching(stream_arn: str, callables: typing.List[typing.Callable]) -> None:
    shard_to_watcher: typing.Dict[str, Process] = {}
    initial_loop = True
    killer = GracefulKiller()
    while not killer.kill_now:
        open_shards = list_open_shards(stream_arn=stream_arn)
        start_at_oldest = True
        if initial_loop:
            start_at_oldest = False
            initial_loop = False
        for shard in open_shards:
            if shard.shard_id not in shard_to_watcher:
                print("DDB:Starting watcher for shard:", shard.shard_id)
                args = (shard, callables, start_at_oldest, UPDATING_SECRETS)
                process = Process(target=shard_watcher, args=args)
                shard_to_watcher[shard.shard_id] = process
                process.start()
        time.sleep(10)


def print_summary(change_record: dict):
    IST = pytz.timezone('Asia/Kolkata')
    changed_at:datetime = change_record["dynamodb"]["ApproximateCreationDateTime"]
    event_type:str = change_record["eventName"]
    item_keys:dict = change_record["dynamodb"]["Keys"]
    item_key_list = []
    for key in sorted(item_keys.keys()):
        value = item_keys[key][list(item_keys[key].keys())[0]]
        item_key_list.append(f"{key}={value}")
    output_str = "[{0}] - {1:^6} - {2}".format(
        changed_at.astimezone(IST).isoformat(
            timespec="seconds"), event_type, ", ".join(item_key_list))
    print(output_str)


def init_ddbwatch(stream_arn=STREAM_ARN):
    handlers = []
    if len(handlers) == 0:
        handlers.append(print_summary)
    start_watching(stream_arn, handlers)

