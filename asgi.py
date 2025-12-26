from backend.config import get_settings
from backend.main import app
from backend.utils.logging_utils import logger

settings = get_settings()

if __name__ == '__main__':
    import uvicorn

    serv_ip = settings.server_ip
    serv_port = settings.server_port
    logger.info("Server {}({}) started, running on http://{}:{}".format(
        settings.server_name, settings.server_env, serv_ip, serv_port))
    uvicorn.run(app, host=serv_ip, port=serv_port)
