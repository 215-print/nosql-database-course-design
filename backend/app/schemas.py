
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


BusinessText = Annotated[str, StringConstraints(strip_whitespace=True)]
PackageDirection = Literal["收件", "寄件"]  # 快递业务方向
PackageStatus = Literal["待取件", "已取件", "待揽收", "异常"]  # 快递状态
AppointmentSlot = Literal[
    "9：00-10：00", "10：00-11：00", "11：00-12：00", "14：00-15：00",
    "15：00-16：00", "16：00-17：00", "17：00-18：00",
]



class UserRegister(BaseModel):
    username: BusinessText = Field(..., min_length=2, max_length=30, description="登录账号")  # 用户登录账号
    password: str = Field(..., min_length=6, max_length=72, description="登录密码")  # 用户登录密码
    name: BusinessText = Field(..., min_length=1, max_length=50, description="注册姓名")  # 用户注册姓名
    phone: str = Field(..., pattern=r"^1\d{10}$", description="绑定手机号")  # 用户绑定手机号


class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=30, description="登录账号")  # 用户登录账号
    password: str = Field(..., min_length=1, max_length=72, description="登录密码")  # 用户登录密码


class AdminLogin(BaseModel):
    username: str = Field(..., min_length=1, description="管理员账号")  # 管理员登录账号
    password: str = Field(..., min_length=1, description="管理员登录密码")  # 管理员登录密码


class UserBlacklistRequest(BaseModel):
    blacklist: bool  # 是否拉黑用户


class UserAccountUpdate(BaseModel):
    username: BusinessText | None = Field(None, min_length=2, max_length=30, description="新的登录账号")  # 可选的新登录账号
    name: BusinessText | None = Field(None, min_length=1, max_length=50, description="新的用户名称")  # 可选的新显示名称


class UserPhoneRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1\d{10}$")


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=72, description="当前密码")  # 验证身份用的当前密码
    new_password: str = Field(..., min_length=6, max_length=72, description="新密码")  # 新登录密码


class AdminUserPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=72, description="重置后的密码")  # 管理员设置的新密码



class PackageCreate(BaseModel):
    phone: str = Field(..., pattern=r"^1\d{10}$", description="收件人手机号")  # 用于关联用户的手机号
    receiver_name: BusinessText = Field(..., min_length=1, max_length=50, description="面单收件人姓名")  # 面单姓名，可与注册姓名不同
    receiver_address: BusinessText | None = Field(None, max_length=200, description="收件地址")
    company: BusinessText = Field(..., min_length=1, max_length=50, description="快递公司")  # 快递公司名称
    tracking_number: BusinessText = Field(..., min_length=1, max_length=100, description="快递公司单号")  # 快递公司提供的运单号
    is_large: bool = Field(False, description="是否为大件")  # 是否为大件快递
    is_fragile: bool = Field(False, description="是否为易碎品")  # 是否为易碎快递
    is_fresh: bool = Field(False, description="是否为生鲜冷冻")
    is_valuable: bool = Field(False, description="是否为贵重物品")
    is_other: bool = Field(False, description="是否为其他特殊物品")



class ShipmentCreate(BaseModel):
    company: BusinessText = Field(..., min_length=1, max_length=50, description="快递公司")
    sender_address: BusinessText = Field(..., min_length=1, max_length=200, description="寄件地址")  # 寄件人地址
    receiver_name: BusinessText = Field(..., min_length=1, max_length=50, description="收件人姓名")  # 目标收件人姓名
    receiver_phone: str = Field(..., pattern=r"^1\d{10}$", description="收件人手机号")  # 目标收件人手机号
    receiver_address: BusinessText = Field(..., min_length=1, max_length=200, description="收件地址")  # 目标收件地址
    appointment_date: date = Field(..., description="预约到站日期")
    appointment_slot: AppointmentSlot = Field(..., description="预约到站时段")
    is_large: bool = Field(False, description="是否为大件")  # 是否为大件物品
    is_fragile: bool = Field(False, description="是否为易碎品")  # 是否为易碎物品
    is_fresh: bool = Field(False, description="是否为生鲜冷冻")
    is_valuable: bool = Field(False, description="是否为贵重物品")


class ShipmentVerify(BaseModel):
    shipment_code: str = Field(..., pattern=r"^\d{8}$", description="八位寄件码")



class PackageUpdate(BaseModel):
    status: PackageStatus | None = Field(None, description="快递状态")  # 更新快递状态
    abnormal: bool | None = Field(None, description="异常标记")  # 更新异常标记
    is_large: bool | None = Field(None, description="是否为大件")  # 更新大件标记
    is_fragile: bool | None = Field(None, description="是否为易碎品")  # 更新易碎标记
    company: BusinessText | None = Field(None, min_length=1, max_length=50, description="快递公司")  # 更新快递公司
    tracking_number: BusinessText | None = Field(None, min_length=1, max_length=100, description="快递公司单号")  # 更新快递公司单号
    is_fresh: bool | None = None
    is_valuable: bool | None = None
    is_other: bool | None = None



class PackageResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")  # 忽略内部扩展字段

    id: str  # 数据库内部包裹 ID
    package_code: str  # 兼容字段；与 id 相同，不额外保存第二个唯一编码
    user_id: str | None = None  # 关联的注册用户 ID，未注册用户为空
    phone: str  # 快递关联手机号
    receiver_name: str  # 快递面单上的收件人姓名
    company: str | None = None  # 快递公司
    tracking_number: str | None = None  # 快递公司提供的运单号
    is_large: bool  # 是否为大件
    is_fragile: bool = False  # 是否为易碎品
    is_fresh: bool = False
    is_valuable: bool = False
    is_other: bool = False
    direction: PackageDirection  # 收件或寄件
    sender_name: str | None = None  # 寄件人姓名
    sender_phone: str | None = None  # 寄件人手机号
    sender_address: str | None = None  # 寄件人地址
    receiver_phone: str | None = None  # 收件人手机号
    receiver_address: str | None = None  # 收件人地址
    pickup_code: str | None = None  # 柜号-排号-四位编号，取件成功后失效
    shipment_code: str | None = None  # 寄件到站核验码，入站后失效
    appointment_at: datetime | None = None  # 预约到站时间
    appointment_date: date | None = None
    appointment_slot: AppointmentSlot | None = None
    status: PackageStatus  # 快递当前状态
    abnormal: bool  # 是否异常
    created_at: datetime  # 入库或寄件申请时间
    picked_at: datetime | None = None  # 实际取件时间
    inbound_at: datetime | None = None
    cabinet_no: int | None = None
    cabinet_row: int | None = None
    waiting_seconds: int = 0
    overdue: bool = False
    overdue_hours: int = 168


class PickupRequest(BaseModel):
    pickup_code: str = Field(..., pattern=r"^\d{1,2}-[1-9]-\d{4}$", description="柜号-排号-四位编号")
    operator_type: Literal["用户", "管理员"] = Field("用户", description="取件操作角色")  # 取件操作角色



class CourierCreate(BaseModel):
    name: BusinessText = Field(..., min_length=1, max_length=50, description="快递员姓名")  # 快递员姓名
    phone: str = Field(..., pattern=r"^1\d{10}$", description="快递员手机号")


class CourierUpdate(BaseModel):
    name: BusinessText | None = Field(None, min_length=1, max_length=50, description="快递员姓名")
    phone: str | None = Field(None, pattern=r"^1\d{10}$", description="快递员手机号")


class CourierBlacklistRequest(BaseModel):
    blacklist: bool  # 是否拉黑快递员
