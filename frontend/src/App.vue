<template>
  <router-view></router-view>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
:root {
  --primary-color: #6200ee;
  --primary-variant: #3700b3;
  --secondary-color: #03dac6;
  --background: #ffffff;
  --surface: #ffffff;
  --error: #b00020;
  --on-primary: #ffffff;
  --on-secondary: #000000;
  --on-background: #000000;
  --on-surface: #000000;
  --on-error: #ffffff;
  --elevation-1: 0 2px 1px -1px rgba(0,0,0,0.2), 0 1px 1px 0 rgba(0,0,0,0.14), 0 1px 3px 0 rgba(0,0,0,0.12);
  --elevation-2: 0 3px 1px -2px rgba(0,0,0,0.2), 0 2px 2px 0 rgba(0,0,0,0.14), 0 1px 5px 0 rgba(0,0,0,0.12);
}

#app {
  font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--on-background);
  margin: 0;
  padding: 0;
  background-color: var(--background);
  min-height: 100vh;
}

body {
  margin: 0;
  padding: 0;
  background-color: #f5f5f5;
}

.el-button {
  border-radius: 4px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.el-button--primary {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

.el-button--primary:hover {
  background-color: var(--primary-variant);
  border-color: var(--primary-variant);
}

.el-card {
  border-radius: 8px;
  box-shadow: var(--elevation-1);
  transition: box-shadow 0.3s ease;
}

.el-card:hover {
  box-shadow: var(--elevation-2);
}

.el-input__inner {
  border-radius: 4px;
}

.el-menu {
  border-right: none;
}

.el-menu-item {
  height: 48px;
  line-height: 48px;
  border-radius: 0 24px 24px 0;
  margin: 4px 8px;
  padding: 0 24px !important;
}

.el-menu-item.is-active {
  background-color: rgba(98, 0, 238, 0.12) !important;
  color: var(--primary-color) !important;
}
</style>
