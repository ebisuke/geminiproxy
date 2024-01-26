
import json
import traceback
import fastapi
import fastapi.staticfiles
import asyncio
from fastapi.responses import StreamingResponse
web_app=fastapi.FastAPI()
@web_app.post("/v1/chat/completions")
async def completion(request: fastapi.Request):
    bearer=request.headers.get('Authorization')
    if bearer is None:
                return fastapi.Response(status_code=401)
    token=bearer.split(' ')[1]
    payload=await request.json()
    import google.generativeai as genai
    from google.generativeai.types.content_types import ContentDict,PartDict,BlobType,BlobDict
    genai.configure(api_key=token)

    # no filters
    history=[]
    # reshape
    turn="user"
    i=0
    print(payload['messages'])
    for m in payload['messages']:
        if i==0 and m['role']=='system':
            # system prompt
            history.append(ContentDict(role="user",
                                        parts=[m['content']]))
            history.append(ContentDict(role="model",
                                        parts=["理解しました。"]))
        else:
            role='user' if m['role'].lower()=='user' else 'model'
            if turn==role:
                # ok
                history.append(ContentDict(role=role,
                                                parts=[m['content']]))
                turn = 'model' if turn == 'user' else 'user'
            else:
                if role=='user':
                    history.append(ContentDict(role='model',
                                                parts=["(発言なし)"]))
                    history.append(ContentDict(role='user',
                                                parts=[m['content']]))
                    turn='model'
                elif role=='model':
                    history.append(ContentDict(role='user',
                                                parts=["(発言なし)"]))
                    history.append(ContentDict(role='model',
                                                parts=[m['content']]))
                    turn='user'
        i+=1
    # if ends with model , add user
    if turn=='user':
        history.append(ContentDict(role='user',
                                    parts=['(発言なし)']))
    print(history)
    model=genai.GenerativeModel("gemini-pro")
    generation_config=genai.GenerationConfig(candidate_count=1,max_output_tokens=payload['max_tokens'] if 'max_tokens' in payload else None
                                                ,temperature=payload['temperature'] if 'temperature' in payload else None
                                                ,top_p=payload['top_p'] if 'top_p' in payload else None
                                                ,top_k=payload['top_k'] if 'top_k' in payload else None)

    safety=[
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]


  
    if 'stream' in payload and  payload['stream']:
        async def generate():
            print("streaming")
 
            idx=0
            for resp in model.generate_content(contents=history,generation_config=generation_config,safety_settings=safety,stream=True):
                text=resp.text
                print(text)
                await asyncio.sleep(0)
                yield "data: "+json.dumps({
                        "id":"dummy",
                        "object":"chat.completion.chunk",
                        "created":"2021-08-01T00:00:00.000000Z",
                        "model":"gemini-pro",
                        'system_fingerprint':'dummy',
                        'choices':[
                            {
                                "index":0,
                                "delta":{
                                    "content": text,
                                    "role": "assistant"
                                }
                            }
                        ]
                    })+'\n\n'
            print("streaming end")
            yield "data: [DONE]\n\n"
        return StreamingResponse(generate(),media_type="text/event-stream")
    else:
        resp=model.generate_content(contents=history,generation_config=generation_config,safety_settings=safety)
        for i in range(3):
            try:
                return {
                    'choices':[
                        {
                            "message":{
                                "content": resp.text,
                                "role": "assistant"
                            }
                        }
                    ]
                }
            except Exception as e:
                print(resp.__dict__)
                traceback.print_exc()
    return fastapi.Response(status_code=500)
@web_app.get("/")
def index():
    return fastapi.Response(status_code=404)