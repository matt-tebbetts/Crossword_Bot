import pandas as pd
from PIL import Image, ImageDraw, ImageFont

def dataframe_to_image_dark_mode(df, 
                                 img_filepath='files/images/leaderboard.png', 
                                 img_title="Today's Mini", 
                                 img_subtitle="Nerd City",
                                 right_aligned_columns=['rank','time','score','points'], 
                                 font_path='arial.ttf', 
                                 font_size=16):
    # Set colors
    header_bg_color = '#4a4e53'
    row_bg_color = '#2c2f33'
    text_color = 'white'
    title_color = 'white'
    subtitle_color = '#a0a0a0'  # Color for the subtitle
    border_color = '#a0a0a0'
    padding = 8

    # Load font
    font = ImageFont.truetype(font_path, font_size)

    # Temporary image and draw object for calculating column widths
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)

    ## old code
    # Calculate column widths and row heights
    #col_widths = [max(
    #    temp_draw.textlength(str(max(df[col], key=lambda x: len(str(x)))), font) for col in df.columns) + 2 * padding
    #              for col in df.columns]
    
    row_height = font.getbbox('A')[3] + 2 * padding

    # Calculate column widths and row heights
    col_widths = [max(
        temp_draw.textlength(str(max(df[col].tolist() + [col], key=lambda x: len(str(x)))), font) for col in
        df.columns) + 2 * padding
                  for col in df.columns]
    
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
        if right_aligned_columns and col in right_aligned_columns:
            text_x = x + width - temp_draw.textlength(str(col), font) - padding  # Right-align if specified
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
            if right_aligned_columns and col in right_aligned_columns:
                text_x = x + width - text_width - padding  # Right-align if specified

            draw.text((text_x, y + padding), text_value, font=font, fill=text_color)
            x += width
        y += row_height

    img.save(img_filepath)

    return img_filepath