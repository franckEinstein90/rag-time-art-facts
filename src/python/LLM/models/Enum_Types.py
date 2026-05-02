from enum import Enum


class ServiceProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"
    HUGGING_FACE = "hugging_face"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class ModelCapability(str, Enum):
    CHAT = "chat"
    CHAT_STREAMING = "chat_streaming"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE_INPUT = "image_input"
    IMAGE_OUTPUT = "image_output"
    AUDIO_INPUT = "audio_input"
    AUDIO_OUTPUT = "audio_output"
    FUNCTION_CALLING = "function_calling"
    CODE = "code"
    REASONING = "reasoning"
    FINE_TUNABLE = "fine_tunable"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


class PricingUnit(str, Enum):
    PER_1K_TOKENS = "per_1k_tokens"
    PER_1M_TOKENS = "per_1m_tokens"
    PER_REQUEST = "per_request"
    PER_SECOND = "per_second"


class ExecutionBackend(str, Enum):
    CPU = "cpu"                  # Inference on CPU only
    GPU = "gpu"                  # Inference on a local / dedicated GPU
    API = "api"                  # Hosted third-party API (e.g. OpenAI, Anthropic)
    NPU = "npu"                  # Neural Processing Unit / specialized accelerator
    HYBRID = "hybrid"            # Mixed local + remote execution
