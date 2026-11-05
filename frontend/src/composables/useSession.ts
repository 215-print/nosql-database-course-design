import { ref } from 'vue';
import { useRouter } from 'vue-router';
import type { UserProfile } from '../types/api';

function readProfile(): UserProfile {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}') as UserProfile;
  } catch {
    return {} as UserProfile;
  }
}
const user = ref(readProfile());
export function useSession() {
  const router = useRouter();
  function saveProfile(profile: UserProfile) {
    user.value = profile;
    localStorage.setItem('user', JSON.stringify(profile));
  }
  function logout() {
    for (const key of ['token', 'user', 'role']) localStorage.removeItem(key);
    user.value = {} as UserProfile;
    void router.replace('/login');
  }
  function syncProfile() {
    user.value = readProfile();
  }
  return { user, saveProfile, logout, syncProfile };
}
