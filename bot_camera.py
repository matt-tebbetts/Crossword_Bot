import pandas as pd
from PIL import Image, ImageDraw, ImageFont

def dataframe_to_image_dark_mode(df, font_path='arial.ttf', font_size=14, title='Title', right_aligned_columns=None):
    
    # Set colors
    header_bg_color = '#4a4e53'
    row_bg_color = '#2c2f33'
    text_color = 'white'
    title_color = 'white'
    border_color = '#a0a0a0'
    padding = 5

    # Load font
    font = ImageFont.truetype(font_path, font_size)

    # Calculate column widths and row heights
    col_widths = [max(draw.textlength(str(max(df[col], key=lambda x: len(str(x)))), font) for col in df.columns) + 2 * padding for col in df.columns]
    row_height = font.getsize('A')[1] + 2 * padding

    # Create a new image
    img_width = sum(col_widths)
    img_height = (len(df) + 1) * row_height + row_height  # Add an extra row for the title
    img = Image.new('RGB', (img_width, img_height), row_bg_color)
    draw = ImageDraw.Draw(img)

    # Draw title
    title_width = draw.textlength(title, font)
    title_height = font.getsize('A')[1]
    draw.text(((img_width - title_width) // 2, padding), title, font=font, fill=title_color)

    # Draw header
    x, y = 0, row_height
    for col, width in zip(df.columns, col_widths):
        draw.rectangle([x, y, x + width, y + row_height], fill=header_bg_color)
        draw.text((x + padding, y + padding), col, font=font, fill=text_color)
        x += width

    # Draw rows
    y += row_height
    for _, row in df.iterrows():
        x = 0
        for col, width in zip(df.columns, col_widths):
            # Draw cell borders
            draw.rectangle([x, y, x + width, y + row_height], outline=border_color)
            
            # Text alignment
            max_length = max([len(str(x)) for x in df[col]])
            text_value = f"{row[col]:<{max_length}}"  # Left-align by default
            if right_aligned_columns and col in right_aligned_columns:
                text_value = f"{row[col]:>{max_length}}"  # Right-align if specified
                
            draw.text((x + padding, y + padding), text_value, font=font, fill=text_color)
            x += width
        y += row_height

    return img

# get dataframe
df = pd.read_csv('files/mini_dark.csv')

# create image of dataframe
img_file = f'files/images/mini_dark.png'
img_title = f"The Mini dark mode test"
right_aligned_columns = ['time', 'rank']
img = dataframe_to_image_dark_mode(df, title=img_title, right_aligned_columns=right_aligned_columns)
img.save(img_file)
