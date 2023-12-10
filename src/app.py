import base64
import json
import logging
from datetime import datetime, timedelta, timezone
from functools import cache

import boto3

JST = timezone(timedelta(hours=9))
kvs_client = boto3.client('kinesisvideo')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: dict, context: dict) -> dict:
    for record in event['Records']:
        base64_data = record['kinesis']['data']
        stream_processor_event = json.loads(base64.b64decode(base64_data).decode())
        # For more information the result, please refer to https://docs.aws.amazon.com/rekognition/latest/dg/streaming-video-kinesis-output.html

        if not stream_processor_event['FaceSearchResponse']:
            continue

        logger.info(stream_processor_event)
        url = get_hls_streaming_session_url(stream_processor_event)
        logger.info(url)

    return {
        'statusCode': 200,
    }


@cache
def get_kvs_am_client(api_name: str, stream_arn: str):
    # See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/kinesisvideo/client/get_data_endpoint.html
    endpoint = kvs_client.get_data_endpoint(
        APIName=api_name.upper(),
        StreamARN=stream_arn
    )['DataEndpoint']
    return boto3.client('kinesis-video-archived-media', endpoint_url=endpoint)


def get_hls_streaming_session_url(stream_processor_event: dict) -> str:
    # See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/kinesis-video-archived-media/client/get_hls_streaming_session_url.html

    kinesis_video = stream_processor_event['InputInformation']['KinesisVideo']
    stream_arn = kinesis_video['StreamArn']
    kvs_am_client = get_kvs_am_client('get_hls_streaming_session_url', stream_arn)
    start_timestamp = datetime.fromtimestamp(kinesis_video['ServerTimestamp'], JST)
    end_timestamp = datetime.fromtimestamp(kinesis_video['ServerTimestamp'], JST) + timedelta(minutes=1)

    return kvs_am_client.get_hls_streaming_session_url(
        StreamARN=stream_arn,
        PlaybackMode='ON_DEMAND',
        HLSFragmentSelector={
            'FragmentSelectorType': 'SERVER_TIMESTAMP',
            'TimestampRange': {
                'StartTimestamp': start_timestamp,
                'EndTimestamp': end_timestamp,
            },
        },
        ContainerFormat='FRAGMENTED_MP4',
        Expires=300,
    )['HLSStreamingSessionURL']
