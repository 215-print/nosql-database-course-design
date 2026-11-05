import type {
  PackageRecord,
  PackageStatistics,
  RetainedPackages,
  UserPackageRank,
} from '../types/api';
import request from './request';

export const getStatistics = () => request.get<PackageStatistics>('/admin/statistics');
export const getWaitingRank = () => request.get<PackageRecord[]>('/admin/packages/waiting-rank');
export const getUserPackageRank = () => request.get<UserPackageRank[]>('/admin/users/package-rank');
export const getRetainedPackages = (minHours: number, offset = 0) =>
  request.get<RetainedPackages>('/admin/packages/retained', {
    params: { min_hours: minHours, offset, limit: 20 },
  });
