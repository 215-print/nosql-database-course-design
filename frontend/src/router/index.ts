import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const isAdmin = import.meta.env.MODE === 'admin';
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: isAdmin ? '/admin' : '/user' },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: '登录' },
  },
  ...(isAdmin
    ? ([
        {
          path: '/admin',
          component: () => import('../layouts/AdminLayout.vue'),
          meta: { role: '管理员' },
          children: [
            {
              path: '',
              name: 'AdminHome',
              component: () => import('../views/admin/DashboardView.vue'),
              meta: { title: '运营概览' },
            },
            {
              path: 'intake',
              component: () => import('../views/admin/IntakeView.vue'),
              meta: { title: '寄件核验与入库' },
            },
            {
              path: 'pickup',
              component: () => import('../views/admin/PickupView.vue'),
              meta: { title: '取快递' },
            },
            {
              path: 'packages',
              component: () => import('../views/admin/PackagesView.vue'),
              props: { scope: 'all' },
              meta: { title: '快递管理' },
            },
            {
              path: 'waiting',
              component: () => import('../views/admin/PackagesView.vue'),
              props: { scope: 'waiting' },
              meta: { title: '包裹查询' },
            },
            {
              path: 'abnormal',
              component: () => import('../views/admin/PackagesView.vue'),
              props: { scope: 'abnormal' },
              meta: { title: '异常件处理' },
            },
            {
              path: 'management',
              name: 'AdminManagement',
              component: () => import('../views/admin/ManagementView.vue'),
              meta: { title: '人员管理' },
            },
            {
              path: 'operations',
              component: () => import('../views/admin/OperationsView.vue'),
              meta: { title: '统计与滞留' },
            },
          ],
        },
      ] as RouteRecordRaw[])
    : ([
        {
          path: '/register',
          name: 'Register',
          component: () => import('../views/RegisterView.vue'),
          meta: { title: '用户注册' },
        },
        {
          path: '/user',
          component: () => import('../layouts/UserLayout.vue'),
          meta: { role: '用户' },
          children: [
            {
              path: '',
              name: 'UserHome',
              component: () => import('../views/user/HomeView.vue'),
              meta: { title: '我的快递' },
            },
            {
              path: 'shipment',
              component: () => import('../views/user/ShipmentView.vue'),
              meta: { title: '我要寄件' },
            },
            {
              path: 'records',
              component: () => import('../views/user/RecordsView.vue'),
              meta: { title: '取件记录' },
            },
            {
              path: 'profile',
              component: () => import('../views/user/ProfileView.vue'),
              meta: { title: '个人中心' },
            },
          ],
        },
      ] as RouteRecordRaw[])),
  { path: '/:pathMatch(.*)*', redirect: isAdmin ? '/admin' : '/user' },
];
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});
router.beforeEach((to) => {
  document.title = `${String(to.meta.title || import.meta.env.VITE_APP_TITLE)} - ${import.meta.env.VITE_APP_NAME}`;
  if (to.name === 'Login' || (!isAdmin && to.name === 'Register')) return true;
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');
  if (!token || role !== (isAdmin ? '管理员' : '用户')) return '/login';
  if (to.meta.role && to.meta.role !== role) return '/login';
  return true;
});
export default router;
