import json
from datetime import datetime
import tiktoken
from openai import AsyncOpenAI
import os
import re

# connect to gpt
gpt_key = os.getenv('OPENAI_API_KEY')
openai_client = AsyncOpenAI(api_key=gpt_key)
gpt_model = "gpt-4o-mini"
max_tokens = 4096
gpt_role = open('files/config/gpt_role.txt', 'r').read()

# get messages
async def read_messages(ctx):
    with open(f'files/guilds/{ctx.guild.name}/messages.json', 'r') as file:
        messages_data = json.load(file)

        # overwrite spoilers so GPT knows not to reveal that information
        for message in messages_data.values():
            spoilers = re.findall(r'\|\|(.*?)\|\|', message['content'])
            for spoiler in spoilers:
                message['content'] = message['content'].replace(f'||{spoiler}||', f'[SPOILER: {spoiler}]')

        # filter to ensure they're dictionaries
        messages_data = [message for message in messages_data.values() if isinstance(message, dict)]
        messages_data = sorted(messages_data, key=lambda msg: msg.get('create_ts', ''), reverse=True)

    return messages_data

# Filter and tokenize messages to ensure the total token count does not exceed the specified limit
async def format_messages(messages):
    token_count = 0
    filtered_messages = []
    encoder = tiktoken.encoding_for_model(gpt_model)

    # estimate token count
    for msg in messages:
        formatted_message = f"{msg.get('author_nm', '')}: {msg.get('content', '')}"
        message_tokens = len(encoder.encode(formatted_message))
        if token_count + message_tokens > (max_tokens * 0.8):
            print(f"Token count of {token_count} plus current message of {message_tokens} is greater than 80% of max {max_tokens}")
            break
        else:
            filtered_messages.append(formatted_message)
            token_count += message_tokens
    
    # put into one long string
    formatted_messages = "\n".join(filtered_messages)

    return formatted_messages 

# get actual response from gpt model
async def generate_gpt_response(query, attachments):

    # create assistant
    assistant = openai_client.beta.assistants.create(
        name="matt_bot",
        instructions=gpt_role,
        tools=[{"type": "retrieval"}],
        model=gpt_model,
        file_ids=[attachments]
    )

    # create thread
    thread = openai_client.beta.threads.create()

    # add first message to thread
    message = openai_client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=query
    )

    # create run
    run = openai_client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions=gpt_role
    )

    # check run steps
    run_steps = openai_client.beta.threads.runs.steps.list(
        thread_id=thread.id,
        run_id=run.id
    )

    print(run_steps)

    # Once the Run completes, you can list the Messages added to the Thread by the Assistant.
    if run.status == 'completed': 
        messages = openai_client.beta.threads.messages.list(
            thread_id=thread.id
        )
        print(messages)
    else:
        print(run.status)

    #output = response.choices[0].message.content #response['choices'][0]['message']['content']
    #return output
  
# main function that runs it all
async def fetch_gpt_response(ctx, query: str):

    # get message history
    messages = await read_messages(ctx)

    # limit messages to 90% of max tokens
    formatted_messages = await format_messages(messages)
    
    # generate response from gpt model
    response = await generate_gpt_response(query, formatted_messages)
    
    await ctx.send(response)