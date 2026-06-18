# main.py

from fastapi import FastAPI , HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel , Field
from typing import Optional , List , Literal , Annotated , Union
from dotenv import load_dotenv
import os
from openai import OpenAI
from models import PulseBlock
from Prompts.promptTemplate import template_prompt
import re

load_dotenv()

app = FastAPI()




app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000" , "https://nutri-scan-ai-virid.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserMessage(BaseModel):
    role: Literal["user"]
    data: str


class AssistantMessage(BaseModel):
    role: Literal["assistant"]
    data: List[PulseBlock]
    
ChatMessage = Annotated[
    Union[UserMessage, AssistantMessage],
    Field(discriminator="role")
]


class ScanRequest(BaseModel):
    prompt: str
    image: Optional[str] = None
    contextofChat: List[ChatMessage]





@app.get("/")
def root():
    return {"message": "Hello World"}


@app.post('/scan/')
async def scan(request : ScanRequest):

   return  await ORscan(request)
   


async def ORscan(request: ScanRequest):
    try:
        
        chat_context = "\n".join(
            f"{msg.role}: {msg.data}" for msg in request.contextofChat
        )
        print("chat-history: ", request.contextofChat)
        
        
        content = []

       
        if request.image:
            image_str = request.image.strip()
            
            if image_str.startswith("data:image/"):
                
                header, base64_data = image_str.split(",", 1)
                base64_data = re.sub(r'\s+', '', base64_data)
                image_str = f"{header},{base64_data}"
            else:
                
                image_str = re.sub(r'\s+', '', image_str)
                image_str = f"data:image/jpeg;base64,{image_str}"
                
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_str
                }
            }) 

       
        content.append({
            "type": "text",
            "text": f"""
                   User Query:
                   {request.prompt}

                   Previous Context:
                    {chat_context or ""}

                  Instructions:
                  {template_prompt}
                   """
        })

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )

        completion = client.chat.completions.create(
            model="google/gemma-4-31b-it",
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            # response_format={"type": "json_object"}
            # extra_body=extra_config
        )
         
        print(type(completion.choices[0].message.content), '\n')
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        print(f"Server-side error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




