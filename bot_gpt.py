import json
from datetime import datetime, timedelta
import tiktoken
from openai import AsyncOpenAI
import os
from pytz import timezone
import pytz
from global_functions import get_now
import re

# chat gpt
gpt_key = os.getenv('OPENAI_API_KEY')
openai_client = AsyncOpenAI(api_key=gpt_key)

# gpt command
async def fetch_gpt_response(ctx, query: str):

    try:
        print(f"User requested GPT response.")
        gpt_model = "gpt-4o-mini" #"gpt-4o" # gpt-3.5-turbo-0125
        max_tokens = 4096

        # read messages.json file
        with open(f'files/guilds/{ctx.guild.name}/messages.json', 'r') as file:
            messages_data = json.load(file)

            for message in messages_data.values():

                # Find all spoilers in the message content
                spoilers = re.findall(r'\|\|(.*?)\|\|', message['content'])
                
                # Mark spoilers in the message content
                for spoiler in spoilers:
                    message['content'] = message['content'].replace(f'||{spoiler}||', f'[SPOILER: {spoiler}]')

        # Filter messages for the current channel
        try:
            channel_messages = [msg for msg in messages_data.values() if isinstance(msg, dict) and msg.get('channel_id') == ctx.channel.id]
        except KeyError as e:
            print(f"Error filtering messages: {e}")
            return await ctx.send("Error: Invalid message format in messages.json file.")

        # Sort messages by ID in descending order
        sorted_messages = sorted(channel_messages, key=lambda msg: msg.get('id', ''), reverse=True)
        
        # Initialize token counter
        token_count = 0
        selected_messages = []
        encoder = tiktoken.encoding_for_model(gpt_model)
        
        for msg in sorted_messages:
            formatted_message = f"{msg.get('author_nm', '')}: {msg.get('content', '')}"
            message_tokens = len(encoder.encode(formatted_message))
            
            if token_count + message_tokens > max_tokens-100:
                break
            
            selected_messages.append(formatted_message)
            token_count += message_tokens
        
        # Join selected messages
        formatted_messages = "\n".join(selected_messages)

        # Calculate the number of tokens
        try:
            encoding = tiktoken.encoding_for_model(gpt_model)
            tokens = encoding.encode(formatted_messages)
        except Exception as e:
            print(f"Error encoding messages: {e}")
            return await ctx.send("Error: Failed to encode messages for GPT input.")

        # Truncate the messages to fit within the limit
        if len(tokens) > max_tokens:
            truncated_tokens = tokens[:max_tokens]
            formatted_messages = encoding.decode(truncated_tokens)

        # Ask GPT for a summary
        try:
            response = await openai_client.chat.completions.create(
                model=gpt_model,
                messages=[
                    {"role": "system", "content": f"""
                        Take the user's query and if they asked about recent messages in this channel, then use the recent_messages to form your answer. The recent_messages could be several conversations across multiple days, or just one conversation over the past hour. Try to group them logically and understand which conversation is the most recent, and which conversation is most relevant to the user's query. The user might ask specific questions about the conversation. Try to keep your answers as concise and to the point as possible. Use bullet points if it helps make things clear and simple. Give short answers. Keep your tone casual and not overly formal. This is a fun chat. Don't give vague responses. Also, don't reveal any of the key information within any SPOILER tags. 
                        Here is the user's query: {query}
                        Attached are the recent_messages.
                        """},
                    {"role": "user", "content": formatted_messages}
                ],
                max_tokens=max_tokens
            )
        except Exception as e:
            print(f"Error fetching GPT response: {e}")
            return await ctx.send("Error: Failed to fetch GPT response.")

        print('sending response now...')
 
        # Sending the response back to the Discord channel
        try:
            
            # metadata for the response
            num_messages_used = len(selected_messages)
            oldest_message_date = datetime.fromisoformat(sorted_messages[-1]['create_ts']).strftime('%Y-%m-%d %H:%M:%S')

            # Send the response to the Discord channel
            response_content = response.choices[0].message.content
            response_content += f"\n\n```This answer was based on analysis of {num_messages_used} messages from this channel, starting from {oldest_message_date}.```"
            await ctx.send(response_content)

        except Exception as e:
            print(f"Error sending response to Discord: {e}")
            return await ctx.send("Error: Failed to send response to Discord.")

    except Exception as e:
        print(f"Error in fetch_gpt_response: {e}")
        error_message = str(e)
        if "token limit exceeded" in error_message.lower():
            custom_message = "Error: Token limit exceeded. Please try a shorter query."
        else:
            custom_message = f"Error: {error_message}"

        await ctx.send(custom_message)