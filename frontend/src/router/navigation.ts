export const adminNavigation = [
  { path: '/admin', title: '运营概览', icon: 'layout-dashboard' },
  { path: '/admin/intake', title: '寄件核验与入库', icon: 'package-plus' },
  { path: '/admin/pickup', title: '取快递', icon: 'key-round' },
  { path: '/admin/packages', title: '快递管理', icon: 'package' },
  { path: '/admin/waiting', title: '包裹查询', icon: 'search' },
  { path: '/admin/abnormal', title: '异常件处理', icon: 'triangle-alert' },
  { path: '/admin/operations', title: '统计与滞留', icon: 'history' },
  { path: '/admin/management', title: '人员管理', icon: 'users' },
] as const;
export const userNavigation = [
  { path: '/user', title: '我的快递', icon: 'package' },
  { path: '/user/shipment', title: '我要寄件', icon: 'send' },
  { path: '/user/records', title: '取件记录', icon: 'history' },
  { path: '/user/profile', title: '个人中心', icon: 'user-round' },
] as const;
