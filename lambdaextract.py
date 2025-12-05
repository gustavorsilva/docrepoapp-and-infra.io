import os
import json
import boto3
from datetime import datetime

from datadog_api_client.v2 import ApiClient, Configuration
from datadog_api_client.v2.api.spans_api import SpansApi

from datadog_api_client.v2.model.spans_aggregate_request import SpansAggregateRequest
from datadog_api_client.v2.model.spans_aggregate_data import SpansAggregateData
from datadog_api_client.v2.model.spans_aggregate_request_attributes import SpansAggregateRequestAttributes
from datadog_api_client.v2.model.spans_compute import SpansCompute
from datadog_api_client.v2.model.spans_query_filter import SpansQueryFilter


s3 = boto3.client("s3")

def lambda_handler(event, context):

    # ===== CONFIG =====
    DD_API_KEY = "*"
    DD_APP_KEY = "*"
    S3_BUCKET = "*" # bucket de destino

    configuration = Configuration(
        api_key={
            "apiKeyAuth": DD_API_KEY,
            "appKeyAuth": DD_APP_KEY
        },
        server_variables={
            "site": "datadoghq.com"
        }
    )

    query = "service:(meu_app OR app) @http.status_code:*"

    # ===== REQUEST =====
    request = SpansAggregateRequest(
        data=SpansAggregateData(
            type="aggregate_request",
            attributes=SpansAggregateRequestAttributes(
                compute=[
                    SpansCompute(
                        aggregation="count",
                    )
                ],
                filter=SpansQueryFilter(
                    **{
                        "from": "now-2w",
                        "to": "now",
                        "query": query
                    }
                )
            )
        )
    )

    try:
        with ApiClient(configuration) as api_client:
            api = SpansApi(api_client)
            response = api.aggregate_spans(request)
            data = response.to_dict()

        # Lista de buckets retornados
        buckets = data.get("data", [])

        # ===== GERAR O TXT =====
        txt_content = "total\n"
        txt_content += "----------------------\n"

        for bucket in buckets:
            attrs = bucket.get("attributes", {})
            compute = attrs.get("compute", {})
            total = compute.get("c0", 0)
            txt_content += f"{total}\n"

        # Nome do arquivo baseado na data
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"datadog_spans/spans_{timestamp}.txt"

        # Upload para o S3
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=filename,
            Body=txt_content,
            ContentType="text/plain"
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Arquivo TXT exportado com sucesso!",
                "file": filename
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }
