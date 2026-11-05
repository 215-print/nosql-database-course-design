import type { ApiMessage, LoginResponse, UserProfile } from '../types/api';
import request from './request';

export interface UserRegisterInput {
  username: string;
  password: string;
  name: string;
  phone: string;
}

export interface LoginInput {
  username: string;
  password: string;
}

export function registerUser(data: UserRegisterInput) {
  return request.post<ApiMessage<UserProfile>>('/users/register', data);
}

export function loginUser(data: LoginInput) {
  return request.post<LoginResponse>('/users/login', data);
}

export function loginAdmin(data: LoginInput) {
  return request.post<LoginResponse>('/admin/login', data);
}
