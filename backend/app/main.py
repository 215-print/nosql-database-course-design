
from functools import wraps

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError

from app.database import redis_client
from app.auth import create_session, require_admin, require_user
from app.operations import get_user_package_rank, get_waiting_packages
from app.schemas import (
    AdminLogin, AdminUserPasswordReset, CourierBlacklistRequest, CourierCreate, CourierUpdate,
    PackageCreate, PackageResponse, PackageUpdate, PickupRequest, ShipmentCreate, ShipmentVerify,
    UserAccountUpdate, UserBlacklistRequest, UserLogin, UserPasswordUpdate, UserRegister, UserPhoneRequest,
)

from app.services import (
    change_user_password, create_courier, create_package, create_shipment,
    delete_package, get_admin_couriers, get_admin_users, get_all_packages,
    get_package, get_shipment_by_code, receive_shipment, get_packages_by_phone, get_statistics, get_user,
    get_user_by_phone, get_user_packages, get_user_pickup_records,
    get_waiting_rank, login_admin, login_user, pickup_code_key, pickup_package, register_user,
    reset_user_password, search_package_by_tracking_number,
    search_packages_by_phone_last4, set_courier_blacklist,
    set_user_blacklist, update_courier, update_package, update_user_account, update_user_phone,
    migrate_waiting_pickup_codes,
)


app = FastAPI(
    title="校园快递驿站管理系统",
    description="校园快递入库、查询、取件、寄件及管理员管理",
    version="2.1.0",
)  # 创建应用

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 课程设计开发阶段允许跨域
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)  # 配置跨域


def map_value_errors(status_code=400, status_by_message=None):
    """统一把业务 ValueError 转换为 HTTP 错误响应。"""
    status_by_message = status_by_message or {}

    def decorate(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            try:
                return handler(*args, **kwargs)
            except ValueError as exc:
                code = status_by_message.get(str(exc), status_code)
                raise HTTPException(status_code=code, detail=str(exc)) from exc

        return wrapped

    return decorate


@app.on_event("startup")
def migrate_existing_pickup_codes():
    migrate_waiting_pickup_codes()


@app.get("/")
def root():
    return {"message": "校园快递驿站管理系统运行正常", "docs": "/docs"}


@app.get("/health")
def health():
    try:
        redis_client.ping()
        return {"status": "ok", "redis": "connected"}
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis 连接失败") from exc


@app.post("/api/users/register")
@map_value_errors(400)
def user_register(data: UserRegister):
    return {"message": "注册成功", "user": register_user(data)}


@app.post("/api/users/login")
@map_value_errors(401)
def user_login(data: UserLogin):
    user = login_user(data.username, data.password)
    token = create_session(user["id"], "用户")
    return {"message": "登录成功", "token": token, "token_type": "Bearer", "user": user}


@app.post("/api/admin/login")
@map_value_errors(401)
def admin_login(data: AdminLogin):
    admin = login_admin(data.username, data.password)
    token = create_session(admin["username"], "管理员")
    return {"message": "管理员登录成功", "token": token, "token_type": "Bearer", "admin": admin}


@app.get("/api/users/phone/{phone}")
def user_by_phone(phone: str, principal: dict = Depends(require_admin)):
    user = get_user_by_phone(phone)
    if not user:
        raise HTTPException(status_code=404, detail="该手机号尚未注册")
    return user


@app.get("/api/users/{user_id}")
def user_detail(user_id: str, principal: dict = Depends(require_user)):
    if principal.get("subject_id") != user_id:
        raise HTTPException(status_code=403, detail="不能查看其他用户资料")
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@app.patch("/api/users/{user_id}/account")
@map_value_errors(400, {"用户不存在": 404})
def user_account_update(
    user_id: str,
    data: UserAccountUpdate,
    principal: dict = Depends(require_user),
):
    """用户修改自己的登录账号或显示名称。"""
    if principal.get("subject_id") != user_id:
        raise HTTPException(status_code=403, detail="不能修改其他用户资料")
    return {"message": "账户信息修改成功", "user": update_user_account(user_id, data)}


@app.patch("/api/users/{user_id}/password")
@map_value_errors(400, {"用户不存在": 404})
def user_password_update(
    user_id: str,
    data: UserPasswordUpdate,
    principal: dict = Depends(require_user),
):
    """用户验证当前密码后修改自己的登录密码。"""
    if principal.get("subject_id") != user_id:
        raise HTTPException(status_code=403, detail="不能修改其他用户密码")
    return change_user_password(user_id, data.current_password, data.new_password)


@app.post("/api/users/{user_id}/phones")
@map_value_errors(400)
def user_phone_add(user_id: str, data: UserPhoneRequest, principal: dict = Depends(require_user)):
    if principal.get("subject_id") != user_id:
        raise HTTPException(status_code=403, detail="不能修改其他用户手机号")
    return {"message": "手机号已绑定", "user": update_user_phone(user_id, data.phone, "add")}


@app.delete("/api/users/{user_id}/phones/{phone}")
@map_value_errors(400)
def user_phone_remove(user_id: str, phone: str, principal: dict = Depends(require_user)):
    if principal.get("subject_id") != user_id:
        raise HTTPException(status_code=403, detail="不能修改其他用户手机号")
    return {"message": "手机号已解绑", "user": update_user_phone(user_id, phone, "remove")}


@app.post("/api/packages", response_model=PackageResponse)
@map_value_errors(400)
def package_create(data: PackageCreate, principal: dict = Depends(require_admin)):
    return create_package(data)


@app.post("/api/users/{user_id}/shipments", response_model=PackageResponse)
@map_value_errors(400)
def shipment_create(
    user_id: str,
    data: ShipmentCreate,
    principal: dict = Depends(require_user),
):
    if principal.get("subject_id") != user_id:
        raise HTTPException(status_code=403, detail="不能替其他用户提交寄件申请")
    return create_shipment(user_id, data)


@app.post("/api/admin/shipments/verify", response_model=PackageResponse)
def shipment_verify(data: ShipmentVerify, principal: dict = Depends(require_admin)):
    package = get_shipment_by_code(data.shipment_code)
    if not package:
        raise HTTPException(status_code=404, detail="寄件码不存在、已使用或订单已失效")
    return package


@app.post("/api/admin/shipments/receive", response_model=PackageResponse)
@map_value_errors(400)
def shipment_receive(data: ShipmentVerify, principal: dict = Depends(require_admin)):
    return receive_shipment(data.shipment_code)


@app.get("/api/packages", response_model=list[PackageResponse])
def package_list(principal: dict = Depends(require_admin)):
    return get_all_packages()


@app.get("/api/packages/phone/{phone}", response_model=list[PackageResponse])
@map_value_errors(400)
def packages_by_phone(phone: str, principal: dict = Depends(require_admin)):
    return get_packages_by_phone(phone)






@app.get("/api/packages/tracking/{tracking_number}", response_model=PackageResponse)
def package_by_tracking_number(
    tracking_number: str,
    principal: dict = Depends(require_admin),
):
    """管理员通过快递公司提供的真实快递单号查询快递。"""
    package = search_package_by_tracking_number(tracking_number)
    if not package:
        raise HTTPException(status_code=404, detail="未找到对应快递单号")
    return package



@app.get("/api/admin/packages/phone-last4")
def admin_search_phone_last4(
    phone_last4: str = Query(..., min_length=4, max_length=4),
    principal: dict = Depends(require_admin),
):
    if not phone_last4.isdigit():
        raise HTTPException(status_code=400, detail="手机号后四位必须是四位数字")
    return {
        "phone_last4": phone_last4,
        "packages": search_packages_by_phone_last4(phone_last4),
    }


@app.patch("/api/packages/{package_id}", response_model=PackageResponse)
@map_value_errors(400)
def package_update(
    package_id: str,
    data: PackageUpdate,
    principal: dict = Depends(require_admin),
):
    package = update_package(package_id, data)
    if not package:
        raise HTTPException(status_code=404, detail="包裹不存在")
    return package


@app.delete("/api/packages/{package_id}")
def package_delete(package_id: str, principal: dict = Depends(require_admin)):
    if not delete_package(package_id):
        raise HTTPException(status_code=404, detail="包裹不存在")
    return {"message": "删除成功"}


@app.get("/api/users/{user_id}/packages", response_model=list[PackageResponse])
@map_value_errors(404)
def user_packages(user_id: str, principal: dict = Depends(require_user)):
    if principal.get("subject_id") != user_id:
        raise HTTPException(status_code=403, detail="不能查询其他用户的快递")
    return get_user_packages(user_id)


@app.get("/api/users/{user_id}/pickup-records")
@map_value_errors(404)
def user_pickup_records(user_id: str, principal: dict = Depends(require_user)):
    if principal.get("subject_id") != user_id:
        raise HTTPException(status_code=403, detail="不能查询其他用户的取件记录")
    return {"data": get_user_pickup_records(user_id)}


@app.post("/api/packages/pickup", response_model=PackageResponse)
@map_value_errors(400)
def package_pickup(data: PickupRequest, principal: dict = Depends(require_user)):
    package_id = redis_client.get(pickup_code_key(data.pickup_code))
    if not package_id:
        raise HTTPException(status_code=400, detail="取件码不存在或已失效")
    package = get_package(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="包裹不存在")
    user = get_user(principal["subject_id"])
    if not user:
        raise HTTPException(status_code=401, detail="用户账号不存在")
    if package.get("phone") not in user.get("phone_numbers", [user["phone"]]):
        raise HTTPException(status_code=403, detail="该取件码不属于当前登录用户")
    return pickup_package(data.pickup_code, "用户")


@app.post("/api/admin/packages/pickup", response_model=PackageResponse)
@map_value_errors(400)
def admin_package_pickup(
    data: PickupRequest,
    principal: dict = Depends(require_admin),
):
    return pickup_package(data.pickup_code, "管理员")


@app.get("/api/admin/users")
def admin_users(principal: dict = Depends(require_admin)):
    return get_admin_users()


@app.patch("/api/admin/users/{user_id}/account")
@map_value_errors(400, {"用户不存在": 404})
def admin_user_account_update(
    user_id: str,
    data: UserAccountUpdate,
    principal: dict = Depends(require_admin),
):
    """管理员修改用户登录账号或显示名称。"""
    return {"message": "用户账户信息修改成功", "user": update_user_account(user_id, data)}


@app.patch("/api/admin/users/{user_id}/password")
@map_value_errors(404)
def admin_user_password_reset(
    user_id: str,
    data: AdminUserPasswordReset,
    principal: dict = Depends(require_admin),
):
    """管理员重置用户密码。"""
    return reset_user_password(user_id, data.new_password)


@app.patch("/api/admin/users/{user_id}/blacklist")
@map_value_errors(404)
def admin_user_blacklist(
    user_id: str,
    data: UserBlacklistRequest,
    principal: dict = Depends(require_admin),
):
    return set_user_blacklist(user_id, data.blacklist)


@app.post("/api/admin/couriers")
@map_value_errors(400)
def admin_create_courier(
    data: CourierCreate,
    principal: dict = Depends(require_admin),
):
    return create_courier(data.name, data.phone)


@app.get("/api/admin/couriers")
def admin_couriers(principal: dict = Depends(require_admin)):
    return get_admin_couriers()


@app.patch("/api/admin/couriers/{courier_id}")
@map_value_errors(400, {"快递员不存在": 404})
def admin_update_courier(
    courier_id: str,
    data: CourierUpdate,
    principal: dict = Depends(require_admin),
):
    return update_courier(courier_id, data)


@app.patch("/api/admin/couriers/{courier_id}/blacklist")
@map_value_errors(404)
def admin_courier_blacklist(
    courier_id: str,
    data: CourierBlacklistRequest,
    principal: dict = Depends(require_admin),
):
    return set_courier_blacklist(courier_id, data.blacklist)


@app.get("/api/admin/statistics")
def admin_statistics(principal: dict = Depends(require_admin)):
    return get_statistics()


@app.get("/api/admin/packages/waiting-rank")
def admin_waiting_rank(
    limit: int = Query(10, ge=1, le=100),
    principal: dict = Depends(require_admin),
):
    return get_waiting_rank(limit)


@app.get("/api/admin/packages/retained")
def admin_retained_packages(
    min_hours: float = Query(72, ge=0, le=87600),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    principal: dict = Depends(require_admin),
):
    return get_waiting_packages(limit, min_hours, offset)


@app.get("/api/admin/users/package-rank")
def admin_user_package_rank(
    limit: int = Query(10, ge=1, le=100),
    principal: dict = Depends(require_admin),
):
    return get_user_package_rank(limit)


