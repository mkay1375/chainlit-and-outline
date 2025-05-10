import chainlit as cl
from outline_agent import OutlineAgent


@cl.on_message
async def on_message(message: cl.Message):
    cl_response_message = cl.Message(content="")

    agent = OutlineAgent()
    message_history = cl.user_session.get("message_history")

    async for response, message_history in agent.run_stream(message=message.content, message_history=message_history):
        await cl_response_message.stream_token(response.to_markdown(), is_sequence=True)

    await cl_response_message.update()

    if message_history:
        cl.user_session.set("message_history", message_history)
