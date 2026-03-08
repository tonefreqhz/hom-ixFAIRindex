import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add repo root to path for anchor import

from PIL import Image, ImageDraw, ImageFont
from anchor import BASE_COVER, FINAL_COVER  # Import anchored paths

# Load the base image
image = Image.open(BASE_COVER)
draw = ImageDraw.Draw(image)

# Define fonts (use system fonts; adjust paths if needed—on Windows, these are in C:\Windows\Fonts)
title_font = ImageFont.truetype("arialbd.ttf", 60)  # Bold sans-serif (Arial Bold; fallback if missing)
subtitle_font = ImageFont.truetype("arial.ttf", 40)
author_font = ImageFont.truetype("arial.ttf", 30)
seal_font = ImageFont.truetype("arial.ttf", 18)  # Same as retro text (Arial) for seal

# Colors
text_color = (0, 255, 0)  # Retro green for main text
screen_text_color = (0, 0, 0)  # Black for screen-style text
screen_bg_color = (255, 255, 255)  # White for screen background
cursor_color = (0, 0, 0)  # Black cursor

# Image dimensions
width, height = image.size

# Add title (top center)
title_text = "hom-ixFAIRindex"
bbox = draw.textbbox((0, 0), title_text, font=title_font)
text_width = bbox[2] - bbox[0]
draw.text(((width - text_width) / 2, 100), title_text, fill=text_color, font=title_font)

# Add subtitle (below title)
subtitle_text = "hom-ixFAIRindex"
bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
text_width = bbox[2] - bbox[0]
draw.text(((width - text_width) / 2, 180), subtitle_text, fill=text_color, font=subtitle_font)

# Add author (bottom center)
author_text = "Roger G Lewis"
bbox = draw.textbbox((0, 0), author_text, font=author_font)
text_width = bbox[2] - bbox[0]
draw.text(((width - text_width) / 2, height - 100), author_text, fill=text_color, font=author_font)

# Load and overlay the red seal image (center-right) with transparent background (vector-style)
seal_path = os.path.join(os.path.dirname(BASE_COVER), "red seal of approval.png")
try:
    seal_image = Image.open(seal_path).convert("RGBA")  # Ensure RGBA for transparency
    # Remove white background (make it transparent for vector-like overlay)
    datas = seal_image.getdata()
    new_data = []
    for item in datas:
        # If pixel is white-ish (adjust threshold if needed), make it transparent
        if item[0] > 200 and item[1] > 200 and item[2] > 200:  # White threshold
            new_data.append((255, 255, 255, 0))  # Fully transparent
        else:
            new_data.append(item)
    seal_image.putdata(new_data)
    seal_width, seal_height = seal_image.size
    seal_x = width - seal_width - 50
    seal_y = (height - seal_height) / 2
    image.paste(seal_image, (int(seal_x), int(seal_y)), seal_image)  # Alpha composite for transparency
except Exception as e:
    print(f"Error loading seal image: {e} - Using fallback (no seal overlay)")
    seal_width, seal_height = 300, 300  # Fallback size if PNG fails
    seal_x = width - seal_width - 50
    seal_y = (height - seal_height) / 2

# Add screen-style background and text (moved up by 40% height, bottom repositioned)
screen_width, screen_height = 250, 100
original_center_y = seal_y + (seal_height - screen_height) / 2
new_bottom_y = original_center_y - 0.4 * screen_height
screen_y = new_bottom_y - screen_height
screen_x = seal_x + (seal_width - screen_width) / 2
corner_radius = 10
draw.rounded_rectangle([screen_x, screen_y, screen_x + screen_width, screen_y + screen_height], fill=screen_bg_color, outline=(0, 0, 0), width=2, radius=corner_radius)

# Add inner tangents
tangent_length = 15
draw.line([screen_x + corner_radius, screen_y, screen_x + corner_radius + tangent_length, screen_y], fill=(0, 0, 0), width=1)
draw.line([screen_x, screen_y + corner_radius, screen_x, screen_y + corner_radius + tangent_length], fill=(0, 0, 0), width=1)
draw.line([screen_x + screen_width - corner_radius - tangent_length, screen_y, screen_x + screen_width - corner_radius, screen_y], fill=(0, 0, 0), width=1)
draw.line([screen_x + screen_width, screen_y + corner_radius, screen_x + screen_width, screen_y + corner_radius + tangent_length], fill=(0, 0, 0), width=1)
draw.line([screen_x + corner_radius, screen_y + screen_height, screen_x + corner_radius + tangent_length, screen_y + screen_height], fill=(0, 0, 0), width=1)
draw.line([screen_x, screen_y + screen_height - corner_radius - tangent_length, screen_x, screen_y + screen_height - corner_radius], fill=(0, 0, 0), width=1)
draw.line([screen_x + screen_width - corner_radius - tangent_length, screen_y + screen_height, screen_x + screen_width - corner_radius, screen_y + screen_height], fill=(0, 0, 0), width=1)
draw.line([screen_x + screen_width, screen_y + screen_height - corner_radius - tangent_length, screen_x + screen_width, screen_y + screen_height - corner_radius], fill=(0, 0, 0), width=1)

# Simulated typing effect: Partial text with cursor
typing_quote = "Grok Endorses:\nReproducible SelfPub\nNo Drift - "
cursor = "_"
full_text = typing_quote + cursor
text_bbox = draw.textbbox((0, 0), full_text, font=seal_font)
text_width = text_bbox[2] - text_bbox[0]
text_height = text_bbox[3] - text_bbox[1]
text_x = screen_x + (screen_width - text_width) / 2
text_y = screen_y + (screen_height - text_height) / 2
draw.text((text_x, text_y), full_text, fill=screen_text_color, font=seal_font)

# Save the final cover
image.save(FINAL_COVER)
print(f"Cover with transparent seal background (vector-style), adjusted position, and all features added: {FINAL_COVER}")

