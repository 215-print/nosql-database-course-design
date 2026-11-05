import type {
  ApiMessage,
  Courier,
  PackageCreateInput,
  PackageRecord,
  PackageUpdateInput,
  PickupRecord,
  ShipmentCreateInput,
  UserProfile,
} from '../types/api';
import request from './request';

export function getPackages() {
  return request.get<PackageRecord[]>('/packages');
}

export function getPackageByTrackingNumber(trackingNumber: string) {
  return request.get<PackageRecord>(`/packages/tracking/${encodeURIComponent(trackingNumber)}`);
}

export function getPackagesByPhone(phone: string) {
  return request.get<PackageRecord[]>(`/packages/phone/${encodeURIComponent(phone)}`);
}

export function getPackagesByPhoneLast4(phoneLast4: string) {
  return request.get<{ phone_last4: string; packages: PackageRecord[] }>(
    '/admin/packages/phone-last4',
    {
      params: { phone_last4: phoneLast4 },
    }
  );
}

export function createPackage(data: PackageCreateInput) {
  return request.post<PackageRecord>('/packages', data);
}

export function updatePackage(packageId: string, data: PackageUpdateInput) {
  return request.patch<PackageRecord>(`/packages/${encodeURIComponent(packageId)}`, data);
}

export function deletePackage(packageId: string) {
  return request.delete<ApiMessage>(`/packages/${encodeURIComponent(packageId)}`);
}

export function getUserPackages(userId: string) {
  return request.get<PackageRecord[]>(`/users/${encodeURIComponent(userId)}/packages`);
}

export function createShipment(userId: string, data: ShipmentCreateInput) {
  return request.post<PackageRecord>(`/users/${encodeURIComponent(userId)}/shipments`, data);
}

export function verifyShipmentCode(shipment_code: string) {
  return request.post<PackageRecord>('/admin/shipments/verify', { shipment_code });
}

export function receiveShipment(shipmentCode: string) {
  return request.post<PackageRecord>('/admin/shipments/receive', { shipment_code: shipmentCode });
}

export function pickupPackage(data: string | { pickup_code: string }) {
  const payload = typeof data === 'string' ? { pickup_code: data.trim() } : data;
  return request.post<PackageRecord>('/packages/pickup', payload);
}

export function adminPickupPackage(data: { pickup_code: string; operator_type?: '管理员' }) {
  return request.post<PackageRecord>('/admin/packages/pickup', data);
}

export function getUserPickupRecords(userId: string) {
  return request.get<{ data: PickupRecord[] }>(
    `/users/${encodeURIComponent(userId)}/pickup-records`
  );
}

export function getAdminUsers() {
  return request.get<UserProfile[]>('/admin/users');
}

export function setUserBlacklist(userId: string, blacklist: boolean) {
  return request.patch<ApiMessage>(`/admin/users/${encodeURIComponent(userId)}/blacklist`, {
    blacklist,
  });
}

export function getAdminCouriers() {
  return request.get<Courier[]>('/admin/couriers');
}

export function createCourier(data: { name: string; phone: string }) {
  return request.post<Courier>('/admin/couriers', data);
}

export function updateCourier(courierId: string, data: { name: string; phone: string }) {
  return request.patch<Courier>(`/admin/couriers/${encodeURIComponent(courierId)}`, data);
}

export function setCourierBlacklist(courierId: string, blacklist: boolean) {
  return request.patch<ApiMessage>(`/admin/couriers/${encodeURIComponent(courierId)}/blacklist`, {
    blacklist,
  });
}

export function updateUserAccount(userId: string, data: { username: string; name: string }) {
  return request.patch<ApiMessage<UserProfile>>(
    `/users/${encodeURIComponent(userId)}/account`,
    data
  );
}

export function changeUserPassword(
  userId: string,
  data: { current_password: string; new_password: string }
) {
  return request.patch<ApiMessage>(`/users/${encodeURIComponent(userId)}/password`, data);
}

export function addUserPhone(userId: string, phone: string) {
  return request.post<ApiMessage<UserProfile>>(`/users/${encodeURIComponent(userId)}/phones`, {
    phone,
  });
}

export function removeUserPhone(userId: string, phone: string) {
  return request.delete<ApiMessage<UserProfile>>(
    `/users/${encodeURIComponent(userId)}/phones/${encodeURIComponent(phone)}`
  );
}

export function updateAdminUserAccount(userId: string, data: { username: string; name: string }) {
  return request.patch<ApiMessage<UserProfile>>(
    `/admin/users/${encodeURIComponent(userId)}/account`,
    data
  );
}

export function resetAdminUserPassword(userId: string, data: { new_password: string }) {
  return request.patch<ApiMessage>(`/admin/users/${encodeURIComponent(userId)}/password`, data);
}
