import openai
from fastapi import FastAPI, Form, Request, WebSocket, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI with your API key
openai.api_key = os.getenv('OPENAI_API_SECRET_KEY')

# Create FastAPI app
app = FastAPI()

# Set up templates directory
templates = Jinja2Templates(directory="templates")

# Initialize chat responses list
chat_responses = []

# Get credentials from environment
username = os.getenv('BASIC_AUTH_USERNAME')
password = os.getenv('BASIC_AUTH_PASSWORD')


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username_input: str = Form(...), password_input: str = Form(...)):
    if username_input == username and password_input == password:
        response = RedirectResponse(url="/chat", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="authenticated", value="true")
        return response
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


def check_authentication(request: Request):
    auth_cookie = request.cookies.get("authenticated")
    if auth_cookie != "true":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    check_authentication(request)
    return templates.TemplateResponse("index.html", {"request": request, "chat_responses": chat_responses})


@app.post("/chat", response_class=HTMLResponse)
async def chat(request: Request, user_input: str = Form(...)):
    check_authentication(request)
    chat_log = [{'role': 'system', 'content': 'You are a helpful assistant.'}]
    chat_log.append({'role': 'user', 'content': user_input})
    chat_responses.append(user_input)

    logging.info(f"User input: {user_input}")

    try:
        response = openai.ChatCompletion.create(
            model='gpt-4-turbo',
            messages=chat_log,
            temperature=0.6
        )

        bot_response = response.choices[0].message['content']
        logging.info(f"AI response: {bot_response}")

        chat_log.append({'role': 'assistant', 'content': bot_response})
        chat_responses.append(bot_response)

    except Exception as e:
        logging.error(f"Error generating response: {e}")
        bot_response = f"Error: {str(e)}"
        chat_responses.append(bot_response)

    return templates.TemplateResponse("index.html", {"request": request, "chat_responses": chat_responses})


@app.get("/image", response_class=HTMLResponse)
async def image_page(request: Request):
    check_authentication(request)
    return templates.TemplateResponse("image.html", {"request": request})


@app.post("/image", response_class=HTMLResponse)
async def create_image(request: Request, user_input: str = Form(...)):
    check_authentication(request)
    try:
        response = openai.Image.create(
            prompt=user_input,
            n=1,
            size="256x256"
        )

        image_url = response['data'][0]['url']
        return templates.TemplateResponse("image.html",
                                          {"request": request, "image_url": image_url, "prompt": user_input})
    except Exception as e:
        return templates.TemplateResponse("image.html", {"request": request, "error": str(e)})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            chat_log = [{'role': 'system', 'content': 'You tell jokes.'}]
            chat_log.append({'role': 'user', 'content': data})

            logging.info(f"User input: {data}")

            try:
                response = openai.ChatCompletion.create(
                    model='gpt-4-turbo',
                    messages=chat_log,
                    temperature=0.6
                )

                ai_response = response.choices[0].message['content']
                logging.info(f"AI response: {ai_response}")

                await websocket.send_text(ai_response)

            except Exception as e:
                logging.error(f"Error generating response: {e}")
                await websocket.send_text(f"Error: {str(e)}")

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# Uncomment these lines in your .env file
# BASIC_AUTH_USERNAME=your_username
# BASIC_AUTH_PASSWORD=your_password
# OPENAI_API_SECRET_KEY=your_openai_api_key
