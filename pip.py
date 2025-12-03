from datadog_api_client.v2 import ApiClient, Configuration
from datadog_api_client.v2.api.spans_api import SpansApi

from datadog_api_client.v2.model.spans_aggregate_request import SpansAggregateRequest
from datadog_api_client.v2.model.spans_aggregate_data import SpansAggregateData
from datadog_api_client.v2.model.spans_aggregate_request_attributes import SpansAggregateRequestAttributes
from datadog_api_client.v2.model.spans_compute import SpansCompute
from datadog_api_client.v2.model.spans_query_filter import SpansQueryFilter
from datadog_api_client.v2.model.spans_group_by import SpansGroupBy

# ===========================
# CONFIGURAÇÕES
# ===========================
DD_API_KEY = "#"
DD_APP_KEY = "#"
PRIVATE_API_URL = "https://api.datadoghq.com"   # << AQUI

configuration = Configuration()
configuration.api_key = {
    "apiKeyAuth": DD_API_KEY,
    "appKeyAuth": DD_APP_KEY,
}

# === Sobrescrevendo URL base ===
configuration.host = PRIVATE_API_URL   # << CERTO

query = "service:(meu_app OR app) @http.status_code:*"

request = SpansAggregateRequest(
    data=SpansAggregateData(
        type="aggregate_request",
        attributes=SpansAggregateRequestAttributes(
            compute=[SpansCompute(aggregation="count")],
            filter=SpansQueryFilter(
                **{
                    "from": "now-2w",
                    "to": "now",
                    "query": query
                }
            ),
            group_by=[
                SpansGroupBy(
                    facet="@http.status_code"
                )
            ]
        )
    )
)

with ApiClient(configuration) as api_client:
    api = SpansApi(api_client)
    try:
        response = api.aggregate_spans(request)
        print(response)
    except Exception as e:
        print("Erro:")
        print(e)
