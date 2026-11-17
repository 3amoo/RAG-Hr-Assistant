import os

from dotenv import load_dotenv

# The Docker image receives configuration through environment variables, while
# local development usually uses a .env file. Support both.
load_dotenv()

config = {
    "CELERY_FLOWER_PASSWORD": os.getenv("CELERY_FLOWER_PASSWORD"),
    "FLOWER_AUTH_USER": os.getenv("FLOWER_AUTH_USER", "admin"),
}

# Flower configuration
port = 5555
max_tasks = 10000
auto_refresh = True

# Authentication (only enabled when a password is configured)
if config["CELERY_FLOWER_PASSWORD"]:
    basic_auth = [f"{config['FLOWER_AUTH_USER']}:{config['CELERY_FLOWER_PASSWORD']}"]
