import json, sys
from PIL import Image, ImageDraw, ImageFont

im = Image.open('zhumbaktas_center.jpg').convert('RGB')
draw = ImageDraw.Draw(im)

# Viewpoint: x=180, y=390
# Zhumbaktas: x=415, y=170
vp_x, vp_y = 180, 390
rock_x, rock_y = 415, 170

# Draw sight line
draw.line([(vp_x, vp_y), (rock_x, rock_y)], fill=(255, 50, 50), width=3)

# Draw circle for viewpoint
draw.ellipse([vp_x-8, vp_y-8, vp_x+8, vp_y+8], fill=(0, 150, 255), outline=(255, 255, 255), width=2)

# Draw circle for rock
draw.ellipse([rock_x-8, rock_y-8, rock_x+8, rock_y+8], fill=(255, 200, 0), outline=(0, 0, 0), width=2)

im.save('zhumbaktas_evidence.jpg')
print("Evidence saved.")
