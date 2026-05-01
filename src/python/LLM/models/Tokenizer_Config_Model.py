from pydantic import BaseModel, Field


class TokenizerConfig(BaseModel):
    """Describes how the model tokenizes text."""

    tokenizer_name: str = Field(..., description="e.g. 'cl100k_base', 'sentencepiece', 'tiktoken'.")
    tokenizer_library: str | None = Field(None, description="e.g. 'tiktoken', 'transformers', 'tokenizers'.")
    vocab_size: int | None = Field(None, gt=0)
    supports_special_tokens: bool = True
    bos_token: str | None = None
    eos_token: str | None = None
    pad_token: str | None = None
    chat_template: str | None = Field(
        None, description="Jinja2 template string used to format chat messages, if applicable."
    )
