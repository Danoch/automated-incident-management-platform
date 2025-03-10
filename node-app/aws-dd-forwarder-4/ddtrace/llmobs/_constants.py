SPAN_KIND = "_ml_obs.meta.span.kind"
SESSION_ID = "_ml_obs.session_id"
METADATA = "_ml_obs.meta.metadata"
METRICS = "_ml_obs.metrics"
ML_APP = "_ml_obs.meta.ml_app"
PROPAGATED_PARENT_ID_KEY = "_dd.p.llmobs_parent_id"
PARENT_ID_KEY = "_ml_obs.llmobs_parent_id"
TAGS = "_ml_obs.tags"

MODEL_NAME = "_ml_obs.meta.model_name"
MODEL_PROVIDER = "_ml_obs.meta.model_provider"

INPUT_DOCUMENTS = "_ml_obs.meta.input.documents"
INPUT_MESSAGES = "_ml_obs.meta.input.messages"
INPUT_VALUE = "_ml_obs.meta.input.value"
INPUT_PARAMETERS = "_ml_obs.meta.input.parameters"
INPUT_PROMPT = "_ml_obs.meta.input.prompt"

OUTPUT_DOCUMENTS = "_ml_obs.meta.output.documents"
OUTPUT_MESSAGES = "_ml_obs.meta.output.messages"
OUTPUT_VALUE = "_ml_obs.meta.output.value"

SPAN_START_WHILE_DISABLED_WARNING = (
    "Span started while LLMObs is disabled." " Spans will not be sent to LLM Observability."
)

GEMINI_APM_SPAN_NAME = "gemini.request"
LANGCHAIN_APM_SPAN_NAME = "langchain.request"
OPENAI_APM_SPAN_NAME = "openai.request"

INPUT_TOKENS_METRIC_KEY = "input_tokens"
OUTPUT_TOKENS_METRIC_KEY = "output_tokens"
TOTAL_TOKENS_METRIC_KEY = "total_tokens"

EVP_PROXY_AGENT_BASE_PATH = "evp_proxy/v2"
EVP_PROXY_AGENT_ENDPOINT = "{}/api/v2/llmobs".format(EVP_PROXY_AGENT_BASE_PATH)
EVP_SUBDOMAIN_HEADER_NAME = "X-Datadog-EVP-Subdomain"
EVP_SUBDOMAIN_HEADER_VALUE = "llmobs-intake"
EVP_PAYLOAD_SIZE_LIMIT = 5 << 20  # 5MB (actual limit is 5.1MB)
EVP_EVENT_SIZE_LIMIT = (1 << 20) - 1024  # 999KB (actual limit is 1MB)

AGENTLESS_BASE_URL = "https://llmobs-intake"
AGENTLESS_ENDPOINT = "api/v2/llmobs"

DROPPED_IO_COLLECTION_ERROR = "dropped_io"
DROPPED_VALUE_TEXT = "[This value has been dropped because this span's size exceeds the 1MB size limit.]"

# Set for traces of evaluator integrations e.g. `runner.integration:ragas`.
# Used to differentiate traces of Datadog-run operations vs user-application operations.
RUNNER_IS_INTEGRATION_SPAN_TAG = "runner.integration"

# The ml app of all ragas traces have this prefix that we use to detect
# whether a span is generated from the ragas evaluation itself.
RAGAS_ML_APP_PREFIX = "dd-ragas"

ANNOTATIONS_CONTEXT_ID = "annotations_context_id"
INTERNAL_CONTEXT_VARIABLE_KEYS = "_dd_context_variable_keys"
INTERNAL_QUERY_VARIABLE_KEYS = "_dd_query_variable_keys"

FAITHFULNESS_DISAGREEMENTS_METADATA = "_dd.faithfulness_disagreements"
EVALUATION_KIND_METADATA = "_dd.evaluation_kind"
EVALUATION_SPAN_METADATA = "_dd.evaluation_span"
