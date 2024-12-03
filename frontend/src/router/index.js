import { createRouter, createWebHistory } from 'vue-router'
import Login from '../components/Login.vue'
import Dashboard from '../components/Dashboard.vue'
import MultipleChoice from '../components/MultipleChoice.vue'
import Learning from '../components/Learning.vue'

const routes = [
  {
    path: '/',
    redirect: '/learning'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/learning',
    name: 'Learning',
    component: Learning,
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/multiple-choice',
    name: 'MultipleChoice',
    component: MultipleChoice,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  
  // 如果是登录页面，已登录则跳转到学习页面
  if (to.path === '/login' && token) {
    next('/learning')
    return
  }
  
  // 需要认证的页面
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!token) {
      next('/login')
    } else {
      next()
    }
  } else {
    // 不需要认证的页面
    next()
  }
})

export default router
