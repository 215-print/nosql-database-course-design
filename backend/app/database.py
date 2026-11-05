import os
import redis
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 配置

REDIS_HOST = os.getenv("REDIS_HOST", "192.168.10.20")  # Redis 服务器 IP
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))  # Redis 端口
REDIS_DB = int(os.getenv("REDIS_DB", "0"))  # Redis 数据库编号
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "123456")  # Redis 密码
REDIS_USERNAME = os.getenv("REDIS_USERNAME") or None  # Redis ACL 用户名

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    username=REDIS_USERNAME,
    password=REDIS_PASSWORD or None,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    health_check_interval=30,
)  # 创建 Redis 客户端