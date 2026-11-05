export type UserRole = '用户' | '管理员';
export type PackageDirection = '收件' | '寄件';
export type PackageStatus = '待取件' | '已取件' | '待揽收' | '异常';
export type AppointmentSlot =
  | '9：00-10：00'
  | '10：00-11：00'
  | '11：00-12：00'
  | '14：00-15：00'
  | '15：00-16：00'
  | '16：00-17：00'
  | '17：00-18：00';

export interface UserProfile {
  id: string;
  username: string;
  name: string;
  phone: string;
  phone_numbers?: string[];
  blacklist?: boolean | string;
}

export interface AdminProfile {
  username: string;
  name?: string;
}

export interface Courier {
  id: string;
  name: string;
  phone: string;
  blacklist?: boolean | string;
}

export interface PackageRecord {
  id: string;
  package_code: string;
  user_id?: string | null;
  phone: string;
  receiver_name: string;
  company?: string | null;
  tracking_number?: string | null;
  is_large: boolean;
  is_fragile?: boolean;
  is_fresh?: boolean;
  is_valuable?: boolean;
  is_other?: boolean;
  direction: PackageDirection;
  sender_name?: string | null;
  sender_phone?: string | null;
  sender_address?: string | null;
  receiver_phone?: string | null;
  receiver_address?: string | null;
  pickup_code?: string | null;
  shipment_code?: string | null;
  appointment_at?: string | null;
  appointment_date?: string | null;
  appointment_slot?: AppointmentSlot | null;
  cabinet_no?: number | null;
  cabinet_row?: number | null;
  status: PackageStatus;
  abnormal: boolean;
  created_at: string;
  inbound_at?: string | null;
  picked_at?: string | null;
  waiting_seconds?: number;
  overdue?: boolean;
  overdue_hours?: number;
}

export interface PickupRecord {
  id?: string;
  package_id?: string;
  company?: string;
  tracking_number?: string;
  picked_at?: string;
  inbound_at?: string;
  pickup_time?: string;
  created_at?: string;
  package?: Partial<PackageRecord>;
  current_status?: PackageStatus | null;
  package_deleted?: boolean;
}

export interface PackageStatistics {
  total: number;
  received: number;
  shipments: number;
  waiting: number;
  picked: number;
  waiting_shipment: number;
  abnormal: number;
  large: number;
  fragile: number;
}

export interface RetainedPackages {
  packages: PackageRecord[];
  total: number;
  overdue_hours: number;
}

export interface UserPackageRank {
  phone: string;
  name: string;
  user_id: string | null;
  package_count: number;
}

export interface PackageCreateInput {
  phone: string;
  receiver_name: string;
  receiver_address?: string;
  company: string;
  tracking_number: string;
  is_large: boolean;
  is_fragile: boolean;
  is_fresh?: boolean;
  is_valuable?: boolean;
  is_other?: boolean;
}

export interface ShipmentCreateInput {
  company: string;
  sender_address: string;
  receiver_name: string;
  receiver_phone: string;
  receiver_address: string;
  appointment_date: string;
  appointment_slot: AppointmentSlot | '';
  is_large: boolean;
  is_fragile?: boolean;
  is_fresh?: boolean;
  is_valuable?: boolean;
}

export interface PackageUpdateInput {
  status?: PackageStatus;
  abnormal?: boolean;
  is_large?: boolean;
  is_fragile?: boolean;
  company?: string;
  tracking_number?: string;
}

export interface LoginResponse {
  token: string;
  token_type: 'Bearer';
  user?: UserProfile;
  admin?: AdminProfile;
  data?: UserProfile | AdminProfile;
  message?: string;
}

export interface ApiMessage<T = unknown> {
  message: string;
  user?: T;
  data?: T;
}
