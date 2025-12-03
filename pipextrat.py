from datadog_api_client.v2 import ApiClient, Configuration
from datadog_api_client.v2.api.spans_api import SpansApi
from datadog_api_client.v2.model.spans_aggregate_request import SpansAggregateRequest
from datadog_api_client.v2.model.spans_aggregate_data import SpansAggregateData
from datadog_api_client.v2.model.spans_aggregate_request_attributes import SpansAggregateRequestAttributes
from datadog_api_client.v2.model.spans_compute import SpansCompute
from datadog_api_client.v2.model.spans_query_filter import SpansQueryFilter
from datadog_api_client.v2.model.spans_group_by import SpansGroupBy
import json
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

# ===========================
# Datas
# ===========================
hora_fixa = "T03:00:00Z"
agora = datetime.now(timezone.utc)

mesatual = agora.strftime("%Y-%m-%d") + hora_fixa
mesanterior = (agora - relativedelta(months=1)).strftime("%Y-%m-%d") + hora_fixa

# ===========================
# CONFIGURAÇÕES
# ===========================
DD_API_KEY = "*"
DD_APP_KEY = "*"
PRIVATE_API_URL = "https://api.datadoghq.com"

config = Configuration()
config.api_key = {
    "apiKeyAuth": DD_API_KEY,
    "appKeyAuth": DD_APP_KEY,
}
config.host = PRIVATE_API_URL

# Query
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
                    "query": query,
                }
            ),
            group_by=[SpansGroupBy(facet="@http.status_code")],
        ),
    )
)

# ===========================
# Execução – EXTRAÇÃO CORRETA
# ===========================
with ApiClient(config) as api_client:
    api = SpansApi(api_client)

    try:
        response = api.aggregate_spans(request)
        data = response.to_dict()

        buckets = data.get("data", [])  # agora sabemos que é uma LISTA

        with open("status_codes.txt", "w") as txt:
            txt.write("StatusCode | Total\n")
            txt.write("----------------------\n")

            for bucket in buckets:
                attrs = bucket.get("attributes", {})
                by = attrs.get("by", {})
                comp = attrs.get("compute", {})

                status = by.get("@http.status_code", "N/A")
                total = comp.get("c0", 0)

                txt.write(f"{status} | {total}\n")

        print("✔ Arquivo status_codes.txt gerado com sucesso!")

    except Exception as e:
        print("Erro:")
        print(e)
