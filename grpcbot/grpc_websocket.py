# main.py
import os
import json
import queue
import asyncio
import threading
from functools import partial
import requests
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import tritonclient.grpc as grpcclient
from tritonclient.utils import InferenceServerException, np_to_triton_dtype

app = FastAPI()

# Allow CORS so our Next.js frontend can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3000/ws",
        "https://zelime.duckdns.org",
        "https://zelime.duckdns.org/ws/infer",
        "https://zelime.duckdns.org/ws",
        "localhost:3000/ws",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def prepare_tensor(name, input_array):
    t = grpcclient.InferInput(name, input_array.shape, np_to_triton_dtype(input_array.dtype))
    t.set_data_from_numpy(input_array)
    return t

class UserData:
    def __init__(self):
        self._completed_requests = queue.Queue()

def ws_callback(user_data, result, error):
    if error:
        user_data._completed_requests.put(error)
    else:
        token = result.as_numpy('text_output')[0].decode("utf-8")
        user_data._completed_requests.put(token)



def get_chat_response(question: str) -> str:
    url = "http://recommendation-backend:8123/chat/"
    headers = {"Content-Type": "application/json"}
    payload = {"question": question}

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

    data = response.json()
    # Assuming the endpoint returns a JSON with a "response" field.
    return data.get("response", "")



def get_sys_prompt(message):
    # return message
    context = get_chat_response(message)
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nCutting Knowledge Date: December 2023\nToday Date: 26 Jul 2024\n\nYou are a chat assitant for a bank, which retrieves data from our loyalty systeem based on the user question and then Respond to the user question in a formal, corporate and polite way. Keep your responses concise. Respond only with information you find in retrieve context and dont make up things. Basically you match user questions with rewards (which are the retrieved context) and you suggest to user what the retrieved context shows! After you present the retrieved results, then ask the user if they want to proceed with a reward redeem.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\nUser Question:{message} \n Context Retrieved: {context}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"""

def blocking_inference(payload, user_data):
    client = grpcclient.InferenceServerClient(url="krikri_trt:8001")
    
    # Extract parameters with defaults:
    prompt = payload.get("prompt", "")
    max_tokens_val = payload.get("max_tokens", 8192)
    temperature_val = payload.get("temperature", 0.4)
    top_k_val = payload.get("top_k", 40)
    top_p_val = payload.get("top_p", 0.9)
    repetition_penalty_val = payload.get("repetition_penalty", 1.0)
    frequency_penalty_val = payload.get("frequency_penalty", 0.0)
    presence_penalty_val = payload.get("presence_penalty", 0.0)
    
    # Build input arrays
    text_input = np.array([[get_sys_prompt(prompt)]], dtype=object)
    max_tokens = np.ones_like(text_input).astype(np.int32) * int(max_tokens_val)
    stream = np.array([[True]], dtype=bool)
    beam_width = np.array([[1]], dtype=np.int32)
    temperature = np.array([[temperature_val]], dtype=np.float32)
    top_k = np.array([[top_k_val]], dtype=np.int32)
    top_p = np.array([[top_p_val]], dtype=np.float32)
    repetition_penalty = np.array([[repetition_penalty_val]], dtype=np.float32)
    frequency_penalty = np.array([[frequency_penalty_val]], dtype=np.float32)
    presence_penalty = np.array([[presence_penalty_val]], dtype=np.float32)
    
    inputs = [
        prepare_tensor("text_input", text_input),
        prepare_tensor("max_tokens", max_tokens),
        prepare_tensor("stream", stream),
        prepare_tensor("beam_width", beam_width),
        prepare_tensor("temperature", temperature),
        prepare_tensor("top_k", top_k),
        prepare_tensor("top_p", top_p),
        prepare_tensor("repetition_penalty", repetition_penalty),
        prepare_tensor("frequency_penalty", frequency_penalty),
        prepare_tensor("presence_penalty", presence_penalty),
    ]
    
    outputs = [grpcclient.InferRequestedOutput("text_output")]
    
    client.start_stream(callback=partial(ws_callback, user_data))
    client.async_stream_infer("ensemble", inputs, outputs=outputs, request_id="")
    client.stop_stream()

@app.websocket("/ws")
async def websocket_infer(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        try:
            payload = json.loads(data)
        except Exception:
            payload = {"prompt": data}
        user_data = UserData()
        thread = threading.Thread(target=blocking_inference, args=(payload, user_data))
        thread.start()
        while thread.is_alive() or not user_data._completed_requests.empty():
            try:
                token = user_data._completed_requests.get(timeout=0.1)
                if isinstance(token, InferenceServerException) or isinstance(token, Exception):
                    await websocket.send_text("Error: " + str(token))
                else:
                    await websocket.send_text(token)
            except queue.Empty:
                await asyncio.sleep(0.1)
        await websocket.close()
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        await websocket.send_text("Error: " + str(e))
        await websocket.close()

@app.post("/infer")
async def infer_endpoint(data: dict):
    prompt = data.get("prompt")
    user_data = UserData()
    thread = threading.Thread(target=blocking_inference, args=(data, user_data))
    thread.start()
    thread.join()
    tokens = []
    while not user_data._completed_requests.empty():
        tokens.append(user_data._completed_requests.get())
    full_text = "".join([t if not isinstance(t, Exception) else "" for t in tokens])
    return JSONResponse({"output": full_text})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7000, reload=True)
