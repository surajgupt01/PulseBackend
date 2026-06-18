from typing import Optional , List , Literal , Annotated , Union
from pydantic import BaseModel , Field
from models import PulseBlock
from Prompts.promptTemplate import template_prompt
import re 
from openai import OpenAI
from fastapi import HTTPException
import os
# import 

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


async def HFscan(request : ScanRequest):
  try:
    
     chat_context = "\n".join(
                   f"{msg.role}: {msg.data}"
      for msg in request.contextofChat
       )
     print("chat-histroy : " , request.contextofChat)
     content = [
           {
            "type": "text",
            "text": f"""
                   User Query:
                   {request.prompt}

                   Previous Context:
                    {chat_context or ""}

                  Instructions:
                  {template_prompt}
                   """
           }
        ]
     if request.image:
            image_str = request.image.strip()
            
            # If your frontend already sends 'data:image/...', make sure it's clean.
            # If it's a raw base64 string, prepend the proper Data URI mime pattern.
            if not image_str.startswith("data:image/"):
                # Clean up any potential accidental whitespace or newline markers
                image_str = re.sub(r'\s+', '', image_str)
                # Wrap it with standard JPEG image schema headers
                image_str = f"data:image/jpeg;base64,{image_str}"
                
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_str
                }
            }) 

    #  if request.image:
    #        content.append(
    #       {
    #         "type": "image_url",
    #         "image_url": {
    #             "url": request.image
    #         }
    #      }
    #      )


     client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=os.environ["OPENROUTER_API_KEY"],
    )

     completion = client.chat.completions.create(
       model="google/gemma-4-31b-it:free",
       messages=[
        {
            "role": "user",
            "content" : content
        }
       ],
        extra_body={"reasoning": {"enabled": True}}

       
      )
     
      
     print(completion.choices[0].message , '\n'  )
     return {"response": completion.choices[0].message.content}


  except Exception as e:
        # Handle exceptions gracefully and return an HTTP 500 error

        raise HTTPException(status_code=500, detail=str(e))
    # return{"your prompt" : data.prompt}
 