import json
from datetime import datetime, timedelta
import tiktoken
from openai import AsyncOpenAI
import os

# chat gpt
gpt_key = os.getenv('OPENAI_API_KEY')
openai_client = AsyncOpenAI(api_key=gpt_key)

# gpt command
async def fetch_gpt_response(ctx, *, query: str):

    is_allowed_author = ctx.author.id == 340940380927295491 or ctx.author.id == 163849350827606016

    if not is_allowed_author:
        print(f"User {ctx.author.name} is not allowed to use the GPT command.")
        return await ctx.send(f"Sorry, {ctx.author.name}, this feature is locked for now.")

    try:
        print(f"User requested GPT response.")

        await ctx.send(f"Okay, let me check...")

        gpt_model = "gpt-4o-mini" #"gpt-4o" # gpt-3.5-turbo-0125

        # Read the messages.json file
        with open(f'files/guilds/{ctx.guild.name}/messages.json', 'r') as file:
            messages_data = json.load(file)

        # Filter messages for the current channel
        channel_messages = [msg for msg in messages_data if msg['channel_id'] == ctx.channel.id]

        # Get the current time
        current_time = datetime.now()

        # Filter messages from the past hour
        one_hour_ago = current_time - timedelta(hours=1)
        recent_messages = [msg for msg in channel_messages if datetime.fromisoformat(msg['timestamp']) > one_hour_ago]

        # Format the messages for GPT input
        formatted_messages = "\n".join([f"{msg['author_name']}: {msg['content']}" for msg in recent_messages])

        # Calculate the number of tokens
        encoding = tiktoken.encoding_for_model(gpt_model)
        tokens = encoding.encode(formatted_messages)
        max_tokens = 4096

        # Truncate the messages to fit within the limit
        if len(tokens) > max_tokens:
            truncated_tokens = tokens[:max_tokens]
            formatted_messages = encoding.decode(truncated_tokens)

        # Ask GPT for a summary
        response = await openai_client.chat.completions.create(
            model=gpt_model,
            messages=[
                {"role": "system", "content": "Summarize the following conversation:"},
                {"role": "user", "content": formatted_messages}
            ],
            max_tokens=1000
        )

        print('sending response now...')
 
        # Sending the response back to the Discord channel
        await ctx.send(response.choices[0].message.content)

    except Exception as e:

        error_message = str(e)
        if "token limit exceeded" in error_message.lower():
            custom_message = "Error: Token limit exceeded. Please try a shorter query."
        else:
            custom_message = f"Error: {error_message}"

        await ctx.send(custom_message)