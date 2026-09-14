import os
import re
import json
from typing import List, Optional, Literal, Union, Annotated
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import AsyncOpenAI

from models import PulseBlock
from Prompts.promptTemplate import template_prompt

load_dotenv()

app = FastAPI(title="Nutri-Scan API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://nutri-scan-ai-virid.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Non-blocking async client for FastAPI event loop
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


# ==========================================
# Schemas
# ==========================================

class UserMessage(BaseModel):
    role: Literal["user"]
    data: str


class AssistantMessage(BaseModel):
    role: Literal["assistant"]
    # Supports structured PulseBlock list or raw string fallback
    data: Union[List[PulseBlock], str]


ChatMessage = Annotated[
    Union[UserMessage, AssistantMessage],
    Field(discriminator="role")
]


class ScanRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None
    image: Optional[str] = None
    extracted_table: Optional[Union[dict, str]] = None
    contextofChat: List[ChatMessage] = []


# ==========================================
# Helpers
# ==========================================

def serialize_message_data(data: Union[str, List[PulseBlock]]) -> str:
    """Safely normalizes user strings or structured PulseBlock lists into a prompt string."""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        # Dump Pydantic models to JSON strings for conversational context
        return json.dumps([
            block.model_dump() if hasattr(block, "model_dump") else block
            for block in data
        ])
    return str(data)


def build_chat_messages(
    prompt: str,
    image: Optional[str],
    context: List[ChatMessage],
    system_instruction: str,
    extracted_table: Optional[Union[dict, str]] = None,
    max_history_turns: int = 8,
) -> list:
    """
    Constructs a cache-friendly, multi-turn payload.
    Anchors static instructions and extracted label data in the system prompt.
    """
    grounded_system = system_instruction.strip()
    if extracted_table:
        table_str = json.dumps(extracted_table, indent=2) if isinstance(extracted_table, dict) else str(extracted_table)
        grounded_system += f"\n\n### Extracted Product & Nutrition Data:\n{table_str}"

    # 1. System block (Byte-for-byte identical prefix for cache hits)
    messages = [{"role": "system", "content": grounded_system}]

    # 2. Sliding window history
    recent_history = context[-max_history_turns:]
    for msg in recent_history:
        messages.append({
            "role": msg.role,
            "content": serialize_message_data(msg.data)
        })

    # 3. Current user turn (multimodal if image present, text otherwise)
    if image:
        image_str = image.strip()
        if image_str.startswith("data:image/"):
            header, base64_data = image_str.split(",", 1)
            image_str = f"{header},{re.sub(r'\\s+', '', base64_data)}"
        else:
            image_str = f"data:image/jpeg;base64,{re.sub(r'\\s+', '', image_str)}"

        user_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_str}}
        ]
    else:
        user_content = prompt

    messages.append({"role": "user", "content": user_content})
    return messages


# ==========================================
# Endpoints
# ==========================================

@app.get("/")
def root():
    return {"message": "Hello World"}


@app.post("/scan/")
async def scan(request: ScanRequest):
    try:
        messages = build_chat_messages(
            prompt=request.prompt,
            image=request.image,
            context=request.contextofChat,
            system_instruction=template_prompt,
            extracted_table=request.extracted_table,
            max_history_turns=8
        )

        extra_body = {}
        if request.session_id:
            # Enables OpenRouter session stickiness to route to the warm cache GPU
            extra_body["session_id"] = request.session_id

        # Async, non-blocking call
        completion = await client.chat.completions.create(
            model="google/gemma-4-31b-it",
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            extra_body=extra_body if extra_body else None
        )

        # Log prompt caching stats to verify savings
        # ✅ Correct: Access as an object attribute
        usage = completion.usage 
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        cached_tokens = getattr(prompt_details, "cached_tokens", 0) if prompt_details else 0

        print(f"[OpenRouter] Total Prompt Tokens: {getattr(usage, 'prompt_tokens', 0)} | Cached: {cached_tokens}")
        assistant_reply = completion.choices[0].message.content
        return {"response": assistant_reply}

    except Exception as e:
        print(f"Server-side error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))