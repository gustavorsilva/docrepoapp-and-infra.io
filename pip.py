from datadog_api_client.v2 import ApiClient, Configuration
from datadog_api_client.v2.api.spans_api import SpansApi
from datadog_api_client.v2.model.spans_aggregate_request import SpansAggregateRequest
from datadog_api_client.v2.model.spans_aggregate_data import SpansAggregateData
from datadog_api_client.v2.model.spans_aggregate_request_attributes import SpansAggregateRequestAttributes
from datadog_api_client.v2.model.spans_compute import SpansCompute
from datadog_api_client.v2.model.spans_query_filter import SpansQueryFilter
from datadog_api_client.v2.model.spans_group_by import SpansGroupBy


# Data
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

hora_fixa = "T03:00:00Z"
agora = datetime.now(timezone.utc)
mesatual = agora.strftime("%Y-%m-%d") + hora_fixa

menos_um_mes = agora - relativedelta(months=1)
mesanterior = menos_um_mes.strftime("%Y-%m-%d") + hora_fixa

# ===========================
# CONFIGURAÇÕES
# ===========================
DD_API_KEY = "f5b1009524a6a2751186839beb0dc66c"
DD_APP_KEY = "215b4e07926fcd64f78205953e939615c3abb701"
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
                    "from": mesanterior,
                    "to": mesatual,
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
