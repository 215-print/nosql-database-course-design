"""包裹排名索引和运营统计。"""
import os
from collections import Counter
from datetime import datetime

import redis

from app.database import redis_client

OVERDUE_HOURS = max(1, int(os.getenv("OVERDUE_HOURS", "48")))
WAITING_INDEX = "operations:waiting-by-time"
USER_COUNT_INDEX = "operations:package-count-by-phone"
INDEX_READY = "operations:index:v1"
INDEX_REVISION = "operations:index:revision"


def package_age(package: dict) -> int:
    created = datetime.fromisoformat(package.get("inbound_at") or package["created_at"])
    if created.tzinfo is None:
        created = created.astimezone()
    return max(0, int((datetime.now().astimezone() - created).total_seconds()))


def write_package_indexes(pipe, package: dict) -> None:
    """放在业务写入的同一个事务里，读取写入后的实际状态。"""
    from app.services import package_key, phone_packages_key
    package_id, phone = package["id"], package["phone"]
    timestamp = datetime.fromisoformat(package.get("inbound_at") or package["created_at"]).timestamp()
    pipe.eval("""
        local count = redis.call('SCARD', KEYS[4])
        if count > 0 then redis.call('ZADD', KEYS[2], count, ARGV[2])
        else redis.call('ZREM', KEYS[2], ARGV[2]) end
        if (redis.call('HGET', KEYS[3], 'direction') or '收件') == '收件'
            and redis.call('HGET', KEYS[3], 'status') == '待取件' then
            redis.call('ZADD', KEYS[1], ARGV[3], ARGV[1])
        else redis.call('ZREM', KEYS[1], ARGV[1]) end
        redis.call('INCR', KEYS[5])
    """, 5, WAITING_INDEX, USER_COUNT_INDEX, package_key(package_id),
        phone_packages_key(phone), INDEX_REVISION, package_id, phone, timestamp)


def ensure_package_indexes() -> None:
    """给历史数据补索引；业务写入改变 revision 时重试，避免覆盖并发变更。"""
    from app.services import PACKAGE_PREFIX
    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(INDEX_READY, INDEX_REVISION)
                if pipe.exists(INDEX_READY):
                    return
                packages = {
                    key: redis_client.hgetall(key)
                    for key in redis_client.scan_iter(f"{PACKAGE_PREFIX}*")
                    if redis_client.type(key) == "hash"
                }.values()
                counts = Counter(p["phone"] for p in packages if p.get("phone"))
                waiting = {
                    p["id"]: datetime.fromisoformat(p.get("inbound_at") or p["created_at"]).timestamp()
                    for p in packages
                    if p.get("direction", "收件") == "收件" and p.get("status") == "待取件"
                }
                pipe.multi()
                pipe.delete(WAITING_INDEX, USER_COUNT_INDEX)
                if waiting:
                    pipe.zadd(WAITING_INDEX, waiting)
                if counts:
                    pipe.zadd(USER_COUNT_INDEX, dict(counts))
                pipe.set(INDEX_READY, "1")
                pipe.execute()
                return
            except redis.WatchError:
                continue
            finally:
                pipe.reset()


def get_waiting_packages(limit=10, min_hours=0, offset=0) -> dict:
    from app.services import get_package
    ensure_package_indexes()
    cutoff = datetime.now().astimezone().timestamp() - min_hours * 3600
    ids = redis_client.zrangebyscore(WAITING_INDEX, "-inf", cutoff, start=offset, num=limit)
    packages = []
    for package_id in ids:
        package = get_package(package_id)
        if package and package["direction"] == "收件" and package["status"] == "待取件":
            package["waiting_seconds"] = package_age(package)
            packages.append(package)
    return {"packages": packages, "total": redis_client.zcount(WAITING_INDEX, "-inf", cutoff),
            "overdue_hours": OVERDUE_HOURS}


def get_user_package_rank(limit=10) -> list[dict]:
    from app.services import get_user_by_phone
    ensure_package_indexes()
    result = []
    for phone, count in redis_client.zrevrange(USER_COUNT_INDEX, 0, limit - 1, withscores=True):
        user = get_user_by_phone(phone)
        result.append({"phone": phone, "name": user["name"] if user else "未注册收件人",
                       "user_id": user["id"] if user else None, "package_count": int(count)})
    return result


