import json
import re

# Read the JSON file
with open('files/guilds/Nerd City/user_styles.json', 'r', encoding='utf-8') as file:
    content = file.read()

# Replace \n with actual new lines
content = content.replace('\\n', '\n')

# Decode Unicode escape sequences
content = re.sub(r'\\u([0-9a-fA-F]{4})', lambda x: chr(int(x.group(1), 16)), content)

# Write the cleaned content to a new text file
with open('files/guilds/Nerd City/user_styles.txt', 'w', encoding='utf-8', errors='ignore') as file:
    file.write(content)