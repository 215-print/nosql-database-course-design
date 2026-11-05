
import hashlib
import json
import os
import re
import secrets
import redis
from datetime import datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.database import redis_client
from app.auth import revoke_user_sessions
from app.operations import (
    OVERDUE_HOURS, get_waiting_packages, package_age, write_package_indexes,
)
from app.schemas import (
    CourierUpdate, PackageCreate, PackageUpdate, ShipmentCreate, UserRegister,
    UserAccountUpdate,
)

PACKAGE_PREFIX = "packages:data:"  # 包裹详情
PACKAGE_CODE_PREFIX = "packages:code:"  # 系统唯一编码索引
TRACKING_PREFIX = "packages:tracking:"  # 快递公司运单号索引
PICKUP_CODE_PREFIX = "packages:pickup-code:"  # 柜号-排号-四位编号取件码索引
SHIPMENT_CODE_PREFIX = "packages:shipment-code:"  # 寄件到站核验码索引
LOCKER_ALLOCATION_LOCK = "packages:system:locker-allocation-lock"
PICKUP_CODE_MIGRATION_KEY = "system:migrations:pickup-code-format-v2"
PHONE_PACKAGES_PREFIX = "packages:phone:"  # 手机号关联的包裹集合
USER_PREFIX = "users:data:"  # 用户详情
USERNAME_PREFIX = "users:username:"  # 用户账号索引
USER_PHONE_PREFIX = "users:phone:"  # 用户手机号索引
PICKUP_RECORD_PREFIX = "pickup:records:"  # 用户取件记录
ALL_PICKUP_RECORDS = "pickup:records:all"
COURIER_PREFIX = "couriers:data:"  # 快递员详情
COURIER_PHONE_PREFIX = "couriers:phone:"  # 快递员手机号索引
PACKAGE_BOOLEAN_FIELDS = ("is_large", "is_fragile", "is_fresh", "is_valuable", "is_other", "abnormal")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")  # 当前时间


def package_key(package_id: str) -> str:
    return f"{PACKAGE_PREFIX}{package_id}"  # 包裹详情 Key


def user_key(user_id: str) -> str:
    return f"{USER_PREFIX}{user_id}"  # 用户详情 Key


def package_code_key(code: str) -> str:
    return f"{PACKAGE_CODE_PREFIX}{code}"  # 系统唯一编码 Key


def tracking_key(number: str) -> str:
    return f"{TRACKING_PREFIX}{number}"  # 快递公司运单号 Key


def pickup_code_key(code: str) -> str:
    return f"{PICKUP_CODE_PREFIX}{code}"  # 取件码索引 Key


def shipment_code_key(code: str) -> str:
    return f"{SHIPMENT_CODE_PREFIX}{code}"  # 寄件码索引 Key


def phone_packages_key(phone: str) -> str:
    return f"{PHONE_PACKAGES_PREFIX}{phone}"  # 手机号关联包裹集合 Key


def iter_hashes(prefix: str):
    """遍历指定前缀下有效的 Redis Hash。"""
    for key in redis_client.scan_iter(f"{prefix}*"):
        if redis_client.type(key) == "hash":
            value = redis_client.hgetall(key)
            if value:
                yield key, value


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)  # 生成随机密码盐
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000).hex()  # 密码哈希
    return f"pbkdf2_sha256${salt}${digest}"  # 保存密码哈希


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith("pbkdf2_sha256$"):  # 验证当前密码格式
        try:
            _, salt, expected = stored.split("$", 2)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000).hex()
            return secrets.compare_digest(actual, expected)
        except ValueError:
            return False

    legacy = hashlib.sha256(password.encode()).hexdigest()  # 兼容旧版 SHA-256 密码
    return secrets.compare_digest(legacy, stored)


def get_user_raw(user_id: str) -> dict | None:
    user = redis_client.hgetall(user_key(user_id))  # 查询用户原始数据
    return user or None


def get_user(user_id: str) -> dict | None:
    user = get_user_raw(user_id)  # 查询用户
    if not user:
        return None
    user.pop("password", None)  # 隐藏密码
    user["blacklist"] = user.get("blacklist") == "true"  # 转换黑名单状态
    try:
        user["phone_numbers"] = json.loads(user.get("phone_numbers", "[]")) or [user.get("phone", "")]
    except (TypeError, json.JSONDecodeError):
        user["phone_numbers"] = [user.get("phone", "")]
    return user


def get_user_by_phone(phone: str) -> dict | None:
    user_id = redis_client.get(f"{USER_PHONE_PREFIX}{phone}")  # 查询手机号索引
    return get_user(user_id) if user_id else None


def update_user_phone(user_id: str, phone: str, action: str) -> dict:
    key = user_key(user_id)
    user = get_user_raw(user_id)
    if not user: raise ValueError("用户不存在")
    phones = json.loads(user.get("phone_numbers", "[]")) or [user.get("phone", "")]
    index = f"{USER_PHONE_PREFIX}{phone}"
    if action == "add":
        owner = redis_client.get(index)
        if owner and owner != user_id: raise ValueError("该手机号已绑定其他账号")
        if phone not in phones: phones.append(phone)
        redis_client.set(index, user_id)
    else:
        phones = [value for value in phones if value != phone]
        if not phones: raise ValueError("至少保留一个绑定手机号")
        if redis_client.get(index) == user_id: redis_client.delete(index)
    mapping = {"phone_numbers": json.dumps(phones)}
    if phone == user.get("phone") and action == "remove": mapping["phone"] = phones[0]
    redis_client.hset(key, mapping=mapping)
    return get_user(user_id)


def register_user(data: UserRegister) -> dict:
    if redis_client.exists(f"{USERNAME_PREFIX}{data.username}"):
        raise ValueError("该登录账号已存在")
    if redis_client.exists(f"{USER_PHONE_PREFIX}{data.phone}"):
        raise ValueError("该手机号已注册")

    user_id = uuid4().hex[:12]  # 生成用户 ID
    user = {"id": user_id,"username": data.username,"password": hash_password(data.password),"name": data.name,
        "phone": data.phone,"blacklist": "false","created_at": now_iso(),}
    with redis_client.pipeline(transaction=True) as pipe:
        while True:
            try:
                pipe.watch(f"{USERNAME_PREFIX}{data.username}", f"{USER_PHONE_PREFIX}{data.phone}")
                if pipe.exists(f"{USERNAME_PREFIX}{data.username}"):
                    raise ValueError("该登录账号已存在")
                if pipe.exists(f"{USER_PHONE_PREFIX}{data.phone}"):
                    raise ValueError("该手机号已注册")
                pipe.multi()
                pipe.hset(user_key(user_id), mapping=user)
                pipe.set(f"{USERNAME_PREFIX}{data.username}", user_id)
                pipe.set(f"{USER_PHONE_PREFIX}{data.phone}", user_id)
                pipe.execute()
                break
            except redis.WatchError:
                continue
            finally:
                pipe.reset()

    return get_user(user_id)


def login_user(username: str, password: str) -> dict:
    user_id = redis_client.get(f"{USERNAME_PREFIX}{username}")  # 查询账号
    if not user_id:
        raise ValueError("账号或密码错误")
    user = get_user_raw(user_id)
    if (
        not user
        or user.get("username") != username
        or not verify_password(password, user.get("password", ""))
    ):
        raise ValueError("账号或密码错误")
    if user.get("blacklist") == "true":
        raise ValueError("该用户已被管理员拉黑")
    if not user["password"].startswith("pbkdf2_sha256$"):
        redis_client.hset(user_key(user_id), "password", hash_password(password))

    return get_user(user_id)


def login_admin(username: str, password: str) -> dict:
    admin_username = os.getenv("ADMIN_USERNAME", "admin")  # 固定管理员账号
    admin_password = os.getenv("ADMIN_PASSWORD", "123456")  # 管理员密码

    if not secrets.compare_digest(username.encode(), admin_username.encode()) or not secrets.compare_digest(password.encode(), admin_password.encode()):
        raise ValueError("管理员账号或密码错误")
    return {"username": admin_username, "role": "管理员"}  # 返回管理员身份


def get_admin_users() -> list[dict]:
    users = []
    for _, user in iter_hashes(USER_PREFIX):
        if "id" not in user:
            continue
        user.pop("password", None)  # 隐藏密码
        user["blacklist"] = user.get("blacklist") == "true"  # 转换黑名单状态
        users.append(user)
    return sorted(users, key=lambda item: item.get("created_at", ""), reverse=True)


def set_user_blacklist(user_id: str, blacklist: bool) -> dict:
    user = get_user(user_id)
    if not user:
        raise ValueError("用户不存在")
    redis_client.hset(user_key(user_id), "blacklist", str(blacklist).lower())
    marked_packages = 0
    if blacklist:
        revoke_user_sessions(user_id)
        user_phones = set(user.get("phone_numbers") or [user.get("phone", "")])
        user_phones.discard("")
        for _, package in iter_hashes(PACKAGE_PREFIX):
            if (
                package.get("direction", "收件") == "收件"
                and package.get("status") == "待取件"
                and (
                    package.get("user_id") == user_id
                    or package.get("phone") in user_phones
                )
            ):
                updated_package = update_package(
                    package["id"],
                    PackageUpdate(status="异常", abnormal=True),
                )
                if updated_package:
                    marked_packages += 1
    return {
        "user_id": user_id,
        "blacklist": blacklist,
        "marked_packages": marked_packages,
    }


def update_user_account(user_id: str, data: UserAccountUpdate) -> dict:
    key = user_key(user_id)
    updates = {field: value
        for field, value in data.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not updates:
        raise ValueError("请至少填写一个需要修改的字段")
    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(key)
                user = pipe.hgetall(key)
                if not user:
                    pipe.unwatch()
                    raise ValueError("用户不存在")
                old_username = user.get("username", "")
                new_username = updates.get("username", old_username)
                old_username_key = f"{USERNAME_PREFIX}{old_username}" if old_username else None
                new_username_key = f"{USERNAME_PREFIX}{new_username}" if new_username else None
                if "username" in updates and new_username != old_username:
                    if old_username_key:
                        pipe.watch(old_username_key)
                    if new_username_key:
                        pipe.watch(new_username_key)
                    current_owner = pipe.get(new_username_key) if new_username_key else None
                    if current_owner and current_owner != user_id:
                        pipe.unwatch()
                        raise ValueError("该登录账号已被其他用户使用")
                    old_owner = pipe.get(old_username_key) if old_username_key else None
                else:
                    old_owner = None
                pipe.multi()
                if "username" in updates and new_username != old_username:
                    if old_username_key and old_owner == user_id:
                        pipe.delete(old_username_key)
                    if new_username_key:
                        pipe.set(new_username_key, user_id)
                pipe.hset(key, mapping=updates)
                pipe.execute()
                return get_user(user_id)
            except redis.WatchError:
                pipe.reset()
                continue
            finally:
                pipe.reset()


def change_user_password(user_id: str, current_password: str, new_password: str) -> dict:
    """用户验证当前密码后修改密码。"""
    key = user_key(user_id)
    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(key)
                user = pipe.hgetall(key)
                if not user:
                    pipe.unwatch()
                    raise ValueError("用户不存在")
                if not verify_password(current_password, user.get("password", "")):
                    pipe.unwatch()
                    raise ValueError("当前密码错误")

                new_hash = hash_password(new_password)
                pipe.multi()
                pipe.hset(key, "password", new_hash)
                pipe.execute()
                break
            except redis.WatchError:
                pipe.reset()
                continue
            finally:
                pipe.reset()

    revoke_user_sessions(user_id)
    return {"user_id": user_id, "message": "密码修改成功"}


def reset_user_password(user_id: str, new_password: str) -> dict:
    """管理员重置用户密码，不返回或读取明文旧密码。"""
    key = user_key(user_id)
    new_hash = hash_password(new_password)
    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(key)
                if not pipe.exists(key):
                    pipe.unwatch()
                    raise ValueError("用户不存在")

                pipe.multi()
                pipe.hset(key, "password", new_hash)
                pipe.execute()
                break
            except redis.WatchError:
                pipe.reset()
                continue
            finally:
                pipe.reset()

    revoke_user_sessions(user_id)
    return {"user_id": user_id, "message": "密码重置成功"}


def generate_pickup_code(package_id: str, cabinet_no: int = 1, cabinet_row: int = 1) -> str:
    for _ in range(100):
        code = f"{cabinet_no}-{cabinet_row}-{secrets.randbelow(10000):04d}"
        if redis_client.set(pickup_code_key(code), package_id, nx=True):
            return code
    raise RuntimeError("取件码生成失败")


def generate_shipment_code() -> str:
    for _ in range(100):
        code = f"{secrets.randbelow(100_000_000):08d}"
        if redis_client.set(shipment_code_key(code), "__reserved__", nx=True):
            return code
    raise RuntimeError("寄件码生成失败")


def allocate_cabinet_position() -> tuple[int, int]:
    """为新入库快递选择当前在库数量最少的柜号和排号。"""
    counts = {(cabinet_no, row): 0 for cabinet_no in range(1, 100) for row in range(1, 10)}
    for key in redis_client.scan_iter(f"{PACKAGE_PREFIX}*"):
        if redis_client.type(key) != "hash":
            continue
        direction, status, abnormal, cabinet_no, cabinet_row = redis_client.hmget(
            key, "direction", "status", "abnormal", "cabinet_no", "cabinet_row"
        )
        if direction not in (None, "", "收件") or status != "待取件" or abnormal == "true":
            continue
        try:
            position = (int(cabinet_no), int(cabinet_row))
        except (TypeError, ValueError):
            continue
        if position in counts:
            counts[position] += 1
    return min(counts, key=lambda position: (counts[position], position[0], position[1]))


def migrate_waiting_pickup_codes() -> int:
    """将历史待取件记录的取件码规范为柜号-排号-四位编号。"""
    lock = redis_client.lock(LOCKER_ALLOCATION_LOCK, timeout=120, blocking_timeout=20)
    if not lock.acquire(blocking=True):
        raise RuntimeError("等待柜位分配锁超时")
    migrated = 0
    try:
        if redis_client.exists(PICKUP_CODE_MIGRATION_KEY):
            return 0

        for key in redis_client.scan_iter(f"{PACKAGE_PREFIX}*"):
            if redis_client.type(key) != "hash":
                continue
            package = redis_client.hgetall(key)
            if package.get("direction", "收件") != "收件" or package.get("status") != "待取件":
                continue
            if package.get("abnormal") == "true":
                continue

            package_id = package.get("id")
            if not package_id:
                continue
            old_code = package.get("pickup_code", "")
            try:
                position = (int(package.get("cabinet_no", "")), int(package.get("cabinet_row", "")))
                position_valid = 1 <= position[0] <= 99 and 1 <= position[1] <= 9
            except (TypeError, ValueError):
                position = (0, 0)
                position_valid = False

            old_index_owner = redis_client.get(pickup_code_key(old_code)) if old_code else None
            code_valid = bool(re.fullmatch(r"\d{1,2}-[1-9]-\d{4}", old_code))
            if code_valid and position_valid and old_index_owner in (None, package_id):
                if old_index_owner is None:
                    redis_client.set(pickup_code_key(old_code), package_id, nx=True)
                continue

            if not position_valid:
                position = allocate_cabinet_position()
            new_code = generate_pickup_code(package_id, *position)
            try:
                with redis_client.pipeline(transaction=True) as pipe:
                    pipe.hset(key, mapping={
                        "cabinet_no": str(position[0]),
                        "cabinet_row": str(position[1]),
                        "pickup_code": new_code,
                    })
                    if old_code and old_index_owner == package_id:
                        pipe.delete(pickup_code_key(old_code))
                    pipe.set(pickup_code_key(new_code), package_id)
                    pipe.execute()
                migrated += 1
            except Exception:
                redis_client.delete(pickup_code_key(new_code))
                raise

        redis_client.set(PICKUP_CODE_MIGRATION_KEY, "done")
        return migrated
    finally:
        if lock.owned():
            lock.release()


def send_pickup_sms(
    phone: str,
    name: str,
    code: str,
    is_large: bool,
    is_fragile: bool = False,
) -> None:
    message = f"【校园快递驿站】{name}，您的快递已入库，取件码：{code}"
    if is_large:
        message += "。该快递为大件，请注意搬运。"
    if is_fragile:
        message += "。该快递为易碎件，请小心处理。"
    print(f"[SMS MOCK] {phone} -> {message}")  # 当前为模拟短信，不会实际发送


def normalize_package(package: dict) -> dict:
    if not package:
        return package
    package_id = package.get("id", "")  # 获取包裹内部 ID
    package["package_code"] = package.get("package_code") or package_id
    package.setdefault("direction", "收件")
    package.setdefault("status", "待取件")
    if package["status"] not in {"待取件", "已取件", "待揽收", "异常"}:
        package["status"] = "待揽收" if package["direction"] == "寄件" else "异常"
    package.setdefault("phone", "")
    package.setdefault("receiver_name", "未填写")
    package.setdefault("created_at", now_iso())
    package["user_id"] = package.get("user_id") or None  # 未注册用户没有用户 ID
    for field in (
        "company","tracking_number","pickup_code","sender_name","sender_phone",
        "sender_address","receiver_phone","receiver_address","picked_at",
        "inbound_at","shipment_code","appointment_at","appointment_date",
        "appointment_slot",
    ):
        package[field] = package.get(field) or None  # 将空字符串转换为 None
    package.update({field: package.get(field) == "true" for field in PACKAGE_BOOLEAN_FIELDS})
    package["waiting_seconds"] = (
        package_age(package)
        if package["direction"] == "收件" and package["status"] == "待取件" else 0
    )
    package["overdue"] = package["waiting_seconds"] > OVERDUE_HOURS * 3600
    package["overdue_hours"] = OVERDUE_HOURS
    return package


def get_package(package_id: str) -> dict | None:
    package = redis_client.hgetall(package_key(package_id))
    return normalize_package(package) if package else None


def get_package_by_code(code: str) -> dict | None:
    package_id = redis_client.get(package_code_key(code))  # 通过系统唯一编码查询
    if package_id and package_id != "__reserved__":
        return get_package(package_id)

    package = get_package(code)
    if package:
        return package

    for package in get_all_packages():
        if package.get("package_code") == code:
            return package

    return None


def get_all_packages() -> list[dict]:
    packages = [normalize_package(package) for _, package in iter_hashes(PACKAGE_PREFIX)]
    return sorted(packages, key=lambda item: item.get("created_at", ""), reverse=True)


def get_packages_by_phone(phone: str) -> list[dict]:
    if (
        not phone.isdigit()
        or len(phone) not in (4, 11)
        or (len(phone) == 11 and not phone.startswith("1"))
    ):
        raise ValueError("请输入完整的11位手机号或4位手机号后四位")
    if len(phone) == 4:
        return search_packages_by_phone_last4(phone)

    ids = redis_client.smembers(phone_packages_key(phone))
    packages = [
        item
        for package_id in ids
        if (item := get_package(package_id))
    ]
    return sorted(packages, key=lambda item: item.get("created_at", ""), reverse=True)


def get_user_packages(user_id: str) -> list[dict]:
    user = get_user(user_id)
    if not user:
        raise ValueError("用户不存在")
    ids = set()
    for phone in user.get("phone_numbers", [user["phone"]]): ids.update(redis_client.smembers(phone_packages_key(phone)))
    return sorted((p for pid in ids if (p := get_package(pid))), key=lambda item: item.get("created_at", ""), reverse=True)


def create_package(data: PackageCreate) -> dict:
    user = get_user_by_phone(data.phone)
    if user and user["blacklist"]:
        raise ValueError("收件人已被管理员拉黑，该快递不能入库")
    package_id = uuid4().hex[:12]
    pickup_code = None
    tracking_reserved = False
    allocation_lock = redis_client.lock(LOCKER_ALLOCATION_LOCK, timeout=30, blocking_timeout=10)
    lock_acquired = False
    try:
        if not redis_client.set(tracking_key(data.tracking_number), package_id, nx=True):
            raise ValueError("该快递公司单号已存在")
        tracking_reserved = True

        if not allocation_lock.acquire(blocking=True):
            raise RuntimeError("等待柜位分配锁超时")
        lock_acquired = True
        cabinet_no, cabinet_row = allocate_cabinet_position()
        pickup_code = generate_pickup_code(package_id, cabinet_no, cabinet_row)
        received_at = now_iso()
        package = {"id": package_id,"user_id": user["id"] if user else "","phone": data.phone,"receiver_name": data.receiver_name,"company": data.company,
                   "tracking_number": data.tracking_number,"is_large": str(data.is_large).lower(),"is_fragile": str(data.is_fragile).lower(),
                   "is_fresh": str(data.is_fresh).lower(),"is_valuable": str(data.is_valuable).lower(),"is_other": str(data.is_other).lower(),
                   "cabinet_no": str(cabinet_no),"cabinet_row": str(cabinet_row),"direction": "收件","pickup_code": pickup_code,"status": "待取件",
                   "abnormal": "false","created_at": received_at,"inbound_at": received_at,}
        if data.receiver_address:
            package["receiver_address"] = data.receiver_address

        with redis_client.pipeline(transaction=True) as pipe:
            phone_index = f"{USER_PHONE_PREFIX}{data.phone}"
            pipe.watch(phone_index)
            current_user_id = pipe.get(phone_index)
            if current_user_id:
                current_user_key = user_key(current_user_id)
                pipe.watch(current_user_key)
                current_user = pipe.hgetall(current_user_key)
                if current_user.get("blacklist") == "true":
                    pipe.unwatch()
                    raise ValueError("收件人已被管理员拉黑，该快递不能入库")
                package["user_id"] = current_user_id
            else:
                package["user_id"] = ""
            pipe.multi()
            pipe.hset(package_key(package_id), mapping=package)
            pipe.sadd(phone_packages_key(data.phone), package_id)
            write_package_indexes(pipe, package)
            pipe.execute()
        allocation_lock.release()
        lock_acquired = False
        send_pickup_sms(data.phone,data.receiver_name, pickup_code,data.is_large, data.is_fragile,)
        return get_package(package_id)
    except Exception:
        with redis_client.pipeline(transaction=True) as pipe:
            pipe.delete(package_key(package_id))
            if tracking_reserved:
                pipe.delete(tracking_key(data.tracking_number))
            if pickup_code:
                pipe.delete(pickup_code_key(pickup_code))
            pipe.srem(phone_packages_key(data.phone), package_id)
            write_package_indexes(pipe, {"id": package_id, "phone": data.phone, "created_at": now_iso(), })
            pipe.execute()
        current_user = get_user_by_phone(data.phone)
        if current_user and current_user["blacklist"]:
            raise ValueError("收件人已被管理员拉黑，该快递不能入库") from None
        raise
    finally:
        if lock_acquired and allocation_lock.owned():
            allocation_lock.release()


def create_shipment(user_id: str, data: ShipmentCreate) -> dict:
    user = get_user_raw(user_id)
    if not user:
        raise ValueError("用户不存在")
    if user.get("blacklist") == "true":
        raise ValueError("该用户已被管理员拉黑")
    slot_start, slot_end = (part.replace("：", ":") for part in data.appointment_slot.split("-"))
    hour, minute = (int(part) for part in slot_start.split(":"))
    end_hour, end_minute = (int(part) for part in slot_end.split(":"))
    shanghai = ZoneInfo("Asia/Shanghai")
    appointment_at = datetime.combine(data.appointment_date, time(hour, minute)).replace(tzinfo=shanghai)
    appointment_end = datetime.combine(data.appointment_date, time(end_hour, end_minute)).replace(tzinfo=shanghai)
    if appointment_end <= datetime.now(shanghai):
        raise ValueError("预约日期和时段不能早于当前时间")
    package_id = uuid4().hex[:12]  # 内部包裹 ID
    shipment_code = generate_shipment_code()
    package = {"id": package_id,"user_id": user_id,"phone": user["phone"],"receiver_name": data.receiver_name,"company": data.company,
        "is_large": str(data.is_large).lower(), "is_fragile": str(data.is_fragile).lower(), "is_fresh": str(data.is_fresh).lower(),
        "is_valuable": str(data.is_valuable).lower(),"direction": "寄件","sender_name": user["name"],"sender_phone": user["phone"],
        "sender_address": data.sender_address,"receiver_phone": data.receiver_phone,"receiver_address": data.receiver_address,
        "appointment_at": appointment_at.isoformat(timespec="seconds"),"appointment_date": data.appointment_date.isoformat(),
        "appointment_slot": data.appointment_slot,"shipment_code": shipment_code,"status": "待揽收","abnormal": "false",
        "created_at": now_iso(),}
    with redis_client.pipeline(transaction=True) as pipe:
        pipe.hset(package_key(package_id), mapping=package)
        pipe.set(shipment_code_key(shipment_code), package_id)
        pipe.sadd(phone_packages_key(user["phone"]), package_id)
        write_package_indexes(pipe, package)
        pipe.execute()
    return get_package(package_id)


def get_shipment_by_code(code: str) -> dict | None:
    package_id = redis_client.get(shipment_code_key(code))
    if not package_id or package_id == "__reserved__":
        return None
    package = get_package(package_id)
    if (
        not package
        or package.get("direction") != "寄件"
        or package.get("status") != "待揽收"
        or not package.get("shipment_code")
    ):
        return None
    return package


def receive_shipment(code: str) -> dict:
    code_key = shipment_code_key(code)
    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(code_key)
                package_id = pipe.get(code_key)
                if not package_id or package_id == "__reserved__":
                    pipe.unwatch()
                    raise ValueError("寄件码不存在或已失效")
                key = package_key(package_id)
                pipe.watch(key)
                package = pipe.hgetall(key)
                if not package:
                    pipe.unwatch()
                    raise ValueError("寄件订单不存在")
                if (
                    package.get("direction") != "寄件"
                    or not package.get("shipment_code")
                ):
                    pipe.unwatch()
                    raise ValueError("该寄件订单当前不能入站")
                user_id = package.get("user_id")
                if user_id:
                    user_data_key = user_key(user_id)
                    pipe.watch(user_data_key)
                    if pipe.hget(user_data_key, "blacklist") == "true":
                        pipe.unwatch()
                        raise ValueError("该用户已被管理员拉黑，寄件不能入站")
                if package.get("abnormal") == "true":
                    pipe.unwatch()
                    raise ValueError("该寄件订单已标记异常，请先完成异常处理")
                stored_code = package.get("shipment_code", "")
                if not stored_code:
                    pipe.unwatch()
                    raise ValueError("寄件码已失效")
                if stored_code != code or pipe.get(code_key) != package_id:
                    pipe.unwatch()
                    raise ValueError("寄件码不存在或已失效")
                inbound_at = now_iso()
                pipe.multi()
                pipe.hset(key, mapping={"status": "待揽收", "inbound_at": inbound_at, "shipment_code": ""})
                pipe.delete(code_key)
                write_package_indexes(pipe, {**package, "status": "待揽收"})
                pipe.execute()
                return get_package(package_id)
            except redis.WatchError:
                pipe.reset()
                continue
            finally:
                pipe.reset()


def update_package(package_id: str, data: PackageUpdate) -> dict | None:
    key = package_key(package_id)  # 包裹详情 Key
    updates = {
        k: v
        for k, v in data.model_dump(exclude_unset=True).items()
        if v is not None
    }

    if not updates:
        return get_package(package_id)

    reintake_code = None
    if updates.get("status") == "待取件":
        old_status = redis_client.hget(key, "status")
        existing_package = get_package(package_id)
        if existing_package and existing_package.get("direction") == "收件":
            recipient = (
                get_user_raw(existing_package.get("user_id"))
                if existing_package.get("user_id")
                else None
            ) or get_user_by_phone(existing_package.get("phone", ""))
            if recipient and recipient.get("blacklist") in (True, "true"):
                raise ValueError("收件人已被管理员拉黑，该快递不能重新入库")
        if old_status == "已取件":
            cabinet_no = int(redis_client.hget(key, "cabinet_no") or 1)
            cabinet_row = int(redis_client.hget(key, "cabinet_row") or 1)
            reintake_code = generate_pickup_code(package_id, cabinet_no, cabinet_row)
            updates["pickup_code"] = reintake_code
            updates["picked_at"] = ""
            updates["inbound_at"] = now_iso()

    if "is_large" in updates:
        updates["is_large"] = str(updates["is_large"]).lower()  # 转换大件布尔值
    if "is_fragile" in updates:
        updates["is_fragile"] = str(updates["is_fragile"]).lower()  # 转换易碎布尔值
    for field in ("is_fresh", "is_valuable", "is_other"):
        if field in updates:
            updates[field] = str(updates[field]).lower()
    if "abnormal" in updates:
        updates["abnormal"] = str(updates["abnormal"]).lower()  # 转换异常布尔值
    if updates.get("status") == "异常":
        updates["abnormal"] = "true"

    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(key)  # 监视包裹详情
                old = pipe.hgetall(key)

                if not old:
                    pipe.unwatch()
                    return None

                if updates.get("status") == "待取件" and old.get("direction", "收件") == "收件":
                    recipient_id = old.get("user_id")
                    if recipient_id:
                        recipient_key = user_key(recipient_id)
                    else:
                        phone_index = f"{USER_PHONE_PREFIX}{old.get('phone', '')}"
                        pipe.watch(phone_index)
                        recipient_id = pipe.get(phone_index)
                        recipient_key = user_key(recipient_id) if recipient_id else None
                    if recipient_key:
                        pipe.watch(recipient_key)
                        if pipe.hget(recipient_key, "blacklist") == "true":
                            if reintake_code:
                                redis_client.delete(pickup_code_key(reintake_code))
                                reintake_code = None
                            pipe.unwatch()
                            raise ValueError("收件人已被管理员拉黑，该快递不能重新入库")

                if updates.get("status") == "已取件" and old.get("status") != "已取件":
                    updates["picked_at"] = now_iso()
                    updates["pickup_code"] = ""
                if "status" in updates:
                    allowed_statuses = (
                        {"待取件", "已取件", "异常"}
                        if old.get("direction", "收件") == "收件"
                        else {"待揽收", "异常"}
                    )
                    if updates["status"] not in allowed_statuses:
                        raise ValueError("该状态不适用于当前快递业务方向")
                    if (
                        old.get("direction") == "寄件"
                        and updates["status"] == "待揽收"
                        and old.get("status") != "待揽收"
                        and not (old.get("shipment_code") or old.get("inbound_at"))
                    ):
                        raise ValueError("请先核验寄件码或确认寄件包裹已入站")
                old_tracking = old.get("tracking_number", "")
                new_tracking = updates.get("tracking_number", old_tracking)
                old_index = tracking_key(old_tracking) if old_tracking else None
                new_index = tracking_key(new_tracking) if new_tracking else None
                if new_tracking and new_tracking != old_tracking:
                    pipe.watch(new_index)  # 监视新运单号索引
                    existing_id = pipe.get(new_index)
                    if existing_id and existing_id != package_id:
                        pipe.unwatch()
                        raise ValueError("该快递公司单号已存在")
                pipe.multi()
                pipe.hset(key, mapping=updates)
                if reintake_code and old.get("pickup_code"):
                    pipe.delete(pickup_code_key(old["pickup_code"]))
                if updates.get("status") == "已取件" and old.get("pickup_code"):
                    pipe.delete(pickup_code_key(old["pickup_code"]))
                if new_tracking and new_tracking != old_tracking:
                    pipe.set(new_index, package_id)
                if old_tracking and old_tracking != new_tracking:
                    pipe.delete(old_index)
                current = {**old, **updates}
                write_package_indexes(pipe, current)
                if reintake_code:
                    pipe.set(pickup_code_key(reintake_code), package_id)
                pipe.execute()
                return get_package(package_id)
            except redis.WatchError:
                pipe.reset()
                continue
            finally:
                pipe.reset()


def delete_package(package_id: str) -> bool:
    key = package_key(package_id)
    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(key)
                package = pipe.hgetall(key)
                if not package:
                    return False
                pipe.multi()
                pipe.delete(key)
                if package.get("package_code"):
                    pipe.delete(package_code_key(package["package_code"]))
                if package.get("tracking_number"):
                    pipe.delete(tracking_key(package["tracking_number"]))
                if package.get("pickup_code"):
                    pipe.delete(pickup_code_key(package["pickup_code"]))
                if package.get("shipment_code"):
                    pipe.delete(shipment_code_key(package["shipment_code"]))
                pipe.srem(phone_packages_key(package["phone"]), package_id)
                write_package_indexes(pipe, {**package, "status": "已删除"})
                pipe.execute()
                return True
            except redis.WatchError:
                continue
            finally:
                pipe.reset()


def pickup_package(code: str, operator_type: str = "用户") -> dict:
    pickup_key = pickup_code_key(code)
    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(pickup_key)
                package_id = pipe.get(pickup_key)
                if not package_id:
                    pipe.unwatch()
                    raise ValueError("取件码不存在或已失效")
                key = package_key(package_id)
                pipe.watch(key)
                package = pipe.hgetall(key)
                if not package:
                    pipe.unwatch()
                    raise ValueError("包裹不存在")
                if package.get("direction") != "收件":
                    pipe.unwatch()
                    raise ValueError("寄件申请不能使用取件码")
                if operator_type == "用户" and (package.get("abnormal") == "true" or package.get("status") == "异常"):
                    pipe.unwatch()
                    raise ValueError("异常包裹不能自主取件，请到快递站与快递员对接包裹详情")
                admin_override = operator_type == "管理员" and package.get("status") == "异常"
                if package.get("status") != "待取件" and not admin_override:
                    pipe.unwatch()
                    raise ValueError("该包裹当前状态不允许取件")
                picked_at = now_iso()
                record = {
                    "id": uuid4().hex[:12],"package_id": package_id,"package_code": package.get("package_code") or package_id,"phone": package["phone"],
                    "receiver_name": package["receiver_name"],"tracking_number": package.get("tracking_number", ""),
                    "company": package.get("company", ""),"pickup_code": code,"operator_type": operator_type,
                    "inbound_at": package.get("inbound_at") or package.get("created_at", ""),"picked_at": picked_at,
                }
                pipe.multi()
                pipe.hset(key, mapping={"status": "已取件", "picked_at": picked_at, "pickup_code": ""})
                pipe.delete(pickup_key)
                pipe.rpush(
                    PICKUP_RECORD_PREFIX + package["phone"],
                    json.dumps(record, ensure_ascii=False),
                )
                pipe.rpush(ALL_PICKUP_RECORDS, json.dumps(record, ensure_ascii=False))
                write_package_indexes(pipe, {**package, "status": "已取件"})
                pipe.execute()
                return get_package(package_id)
            except redis.WatchError:
                pipe.reset()
                continue
            finally:
                pipe.reset()


def get_user_pickup_records(user_id: str) -> list[dict]:
    user = get_user(user_id)
    if not user:
        raise ValueError("用户不存在")
    records = []
    for phone in user.get("phone_numbers", [user["phone"]]):
        records.extend(redis_client.lrange(PICKUP_RECORD_PREFIX + phone, 0, -1))
    result = []
    for item in records:
        record = json.loads(item)
        package = get_package(record["package_id"])
        if package:
            record.setdefault("inbound_at", package.get("inbound_at") or package.get("created_at", ""))
        record["package"] = package
        record["current_status"] = package["status"] if package else None
        record["package_deleted"] = package is None
        result.append(record)
    return sorted(result, key=lambda item: item.get("picked_at", ""), reverse=True)


def search_package_by_tracking_number(number: str) -> dict | None:
    package_id = redis_client.get(tracking_key(number))
    if package_id:
        return get_package(package_id)

    return next(
        (item for item in get_all_packages() if item.get("tracking_number") == number),
        None,
    )


def search_packages_by_phone_last4(last4: str) -> list[dict]:
    result = []

    for package in get_all_packages():
        phones = (
            package.get("phone") or "",
            package.get("sender_phone") or "",
            package.get("receiver_phone") or "",
        )

        if any(phone.endswith(last4) for phone in phones if phone):
            result.append(package)

    return result


def get_statistics() -> dict:
    packages = get_all_packages()

    return {
        "total": len(packages),
        "received": sum(item["direction"] == "收件" for item in packages),
        "shipments": sum(item["direction"] == "寄件" for item in packages),
        "waiting": sum(item["status"] == "待取件" for item in packages),
        "picked": sum(item["status"] == "已取件" for item in packages),
        "waiting_shipment": sum(
            item["direction"] == "寄件"
            and item["status"] == "待揽收"
            and bool(item["inbound_at"])
            for item in packages
        ),
        "abnormal": sum(item["abnormal"] or item["status"] == "异常" for item in packages),
        "large": sum(item["is_large"] for item in packages),
        "fragile": sum(item["is_fragile"] for item in packages),
    }


def get_waiting_rank(limit: int = 10) -> list[dict]:
    return get_waiting_packages(limit)["packages"]


def create_courier(name: str, phone: str) -> dict:
    if redis_client.exists(f"{COURIER_PHONE_PREFIX}{phone}"):
        raise ValueError("该快递员手机号已登记")

    courier_id = uuid4().hex[:12]
    courier = {
        "id": courier_id,
        "name": name,
        "phone": phone,
        "blacklist": "false",
        "created_at": now_iso(),
    }

    with redis_client.pipeline(transaction=True) as pipe:
        while True:
            try:
                pipe.watch(f"{COURIER_PHONE_PREFIX}{phone}")
                if pipe.exists(f"{COURIER_PHONE_PREFIX}{phone}"):
                    raise ValueError("该快递员手机号已登记")
                pipe.multi()
                pipe.hset(f"{COURIER_PREFIX}{courier_id}", mapping=courier)
                pipe.set(f"{COURIER_PHONE_PREFIX}{phone}", courier_id)
                pipe.execute()
                break
            except redis.WatchError:
                continue
            finally:
                pipe.reset()

    return {**courier, "blacklist": False}


def get_admin_couriers() -> list[dict]:
    couriers = [courier for _, courier in iter_hashes(COURIER_PREFIX)]
    for courier in couriers:
        courier["blacklist"] = courier.get("blacklist") == "true"
    return sorted(couriers, key=lambda item: item.get("created_at", ""), reverse=True)


def update_courier(courier_id: str, data: CourierUpdate) -> dict:
    key = f"{COURIER_PREFIX}{courier_id}"
    updates = {
        field: value
        for field, value in data.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not updates:
        raise ValueError("请至少填写一个需要修改的字段")
    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(key)
                courier = pipe.hgetall(key)
                if not courier:
                    pipe.unwatch()
                    raise ValueError("快递员不存在")
                old_phone = courier.get("phone", "")
                new_phone = updates.get("phone", old_phone)
                old_phone_key = f"{COURIER_PHONE_PREFIX}{old_phone}" if old_phone else None
                new_phone_key = f"{COURIER_PHONE_PREFIX}{new_phone}" if new_phone else None
                if "phone" in updates and new_phone != old_phone:
                    if old_phone_key:
                        pipe.watch(old_phone_key)
                    if new_phone_key:
                        pipe.watch(new_phone_key)
                    current_owner = pipe.get(new_phone_key) if new_phone_key else None
                    if current_owner and current_owner != courier_id:
                        pipe.unwatch()
                        raise ValueError("该快递员手机号已登记")
                    old_owner = pipe.get(old_phone_key) if old_phone_key else None
                else:
                    old_owner = None
                pipe.multi()
                if "phone" in updates and new_phone != old_phone:
                    if old_phone_key and old_owner == courier_id:
                        pipe.delete(old_phone_key)
                    if new_phone_key:
                        pipe.set(new_phone_key, courier_id)
                pipe.hset(key, mapping=updates)
                pipe.execute()
                updated = redis_client.hgetall(key)
                updated["blacklist"] = updated.get("blacklist") == "true"
                return updated
            except redis.WatchError:
                pipe.reset()
                continue
            finally:
                pipe.reset()


def set_courier_blacklist(courier_id: str, blacklist: bool) -> dict:
    key = f"{COURIER_PREFIX}{courier_id}"

    if not redis_client.exists(key):
        raise ValueError("快递员不存在")

    redis_client.hset(key, "blacklist", str(blacklist).lower())
    return {"courier_id": courier_id, "blacklist": blacklist}
