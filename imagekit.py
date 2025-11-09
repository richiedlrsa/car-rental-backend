from imagekitio import ImageKit
from dotenv import find_dotenv, load_dotenv
import os

path = find_dotenv()
load_dotenv(path)
PRIVATE_KEY = os.getenv('IK_PRIVATE')
PUBLIC_KEY = os.getenv('IK_PUBLIC')
URL = os.getenv('IK_URL')

imagekit = ImageKit(
    private_key=PRIVATE_KEY,
    public_key=PUBLIC_KEY,
    url_endpoint=URL
)

print(path)