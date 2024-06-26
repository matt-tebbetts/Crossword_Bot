import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import socket

host_nm = socket.gethostname()
local_mode = True if "DESKTOP" in str(host_nm) or "MJT" in str(host_nm) else False

# returns the image filepath
def dataframe_to_image_dark_mode(df, 
                                 img_filepath='files/images/leaderboard.png', 
                                 img_title="Today's Mini", 
                                 img_subtitle="Nerd City",
                                 left_aligned_columns=['Game', 'Name', 'Player', 'Genre'],
                                 right_aligned_columns=['Rank', 'Time', 'Score','Points', 'Wins',
                                                        'Top 3', 'Top 5', 'Played', 'Games', 
                                                        'Scores Added', 'Avg', '1st', '2nd', '3rd', '4th', '5th']):

    # Set colors
    header_bg_color = '#4a4e53'
    row_bg_color = '#2c2f33'
    text_color = 'white'
    title_color = 'white'
    subtitle_color = '#a0a0a0'  # Color for the subtitle
    border_color = '#a0a0a0'
    padding = 8

    # Load font
    font_path = 'C:/Windows/Fonts/arial.ttf' if local_mode else '/usr/share/fonts/truetype/ARIAL.TTF'
    font_size = 18
    font = ImageFont.truetype(font_path, font_size)

    # Temporary image and draw object for calculating column widths
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    
    # calculate row height
    row_height = font.getbbox('A')[3] + 2 * padding

    # old col widths calculation
    #col_widths = [max(temp_draw.textlength(str(max(df[col].tolist() + [col], key=lambda x: len(str(x)))), font) for col in df.columns) + 2 * padding for col in df.columns]

    # new col widths calculation    
    col_widths = [max(temp_draw.textlength(str(x), font) for x in df[col].tolist() + [col]) + 2 * padding for col in df.columns]
    
    # Create a new image
    img_width = sum(col_widths)
    img_height = (len(df) + 2) * row_height + row_height  # Add an extra row for the title
    img = Image.new('RGB', (int(img_width), int(img_height)), row_bg_color)
    draw = ImageDraw.Draw(img)

    # Draw title
    title_width = draw.textlength(img_title, font)
    title_height = font.getbbox('A')[1]
    draw.text(((img_width - title_width) // 2, padding), img_title, font=font, fill=title_color)

    # Draw subtitle
    subtitle_width = draw.textlength(img_subtitle, font)
    draw.text(((img_width - subtitle_width) // 2, padding + title_height + row_height), 
            img_subtitle, 
            font=font, 
            fill=subtitle_color)

    # Draw header
    x, y = 0, row_height * 2
    for col, width in zip(df.columns, col_widths):
        draw.rectangle([x, y, x + width, y + row_height], fill=header_bg_color)
        text_x = x + padding  # Left-align by default
        if col not in left_aligned_columns:
            text_x = x + width - temp_draw.textlength(str(col), font) - padding  # Right-align if not in left_aligned_columns
        draw.text((text_x, y + padding), col, font=font, fill=text_color)
        x += width

    # Draw rows
    y += row_height
    for _, row in df.iterrows():
        x = 0
        for col, width in zip(df.columns, col_widths):
            # Draw cell borders
            draw.rectangle([x, y, x + width, y + row_height], outline=border_color)

            # Text alignment
            text_value = str(row[col])
            text_width = draw.textlength(text_value, font)
            text_x = x + padding  # Left-align by default
            if col not in left_aligned_columns:
                text_x = x + width - text_width - padding  # Right-align if not in left_aligned_columns

            draw.text((text_x, y + padding), text_value, font=font, fill=text_color)
            x += width
        y += row_height

    img.save(img_filepath)
    
    return img_filepath