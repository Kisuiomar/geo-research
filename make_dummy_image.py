from PIL import Image
import numpy as np

# create a 200x200 image with random noise
img = Image.fromarray(np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8))
img.save("dummy.jpg")
print("dummy.jpg created")
