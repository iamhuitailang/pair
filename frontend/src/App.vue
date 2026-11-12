<template>
  <div class="container">
    <h1>游戏事件回放分析平台</h1>
    <router-view />
  </div>
</template>

<style>
body {
  font-family: -apple-system, "PingFang SC", "Helvetica Neue", sans-serif;
  margin: 0;
  background: #f5f6f8;
  color: #222;
}
.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px 24px 48px;
}
h1 { font-size: 20px; }
table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  font-size: 13px;
}
th, td {
  padding: 8px 10px;
  border-bottom: 1px solid #eee;
  text-align: left;
}
th { background: #fafafa; font-weight: 600; }
tr.clickable { cursor: pointer; }
tr.clickable:hover { background: #f0f6ff; }
.filters {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
  background: #fff;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}
.filters label { display: flex; flex-direction: column; font-size: 12px; color: #666; gap: 4px; }
.filters input, .filters select { padding: 6px 8px; border: 1px solid #ccc; border-radius: 4px; }
button, .btn {
  padding: 6px 14px;
  border: 1px solid #2b6cb0;
  background: #2b6cb0;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  text-decoration: none;
}
button.secondary, .btn.secondary { background: #fff; color: #2b6cb0; }
.badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 12px;
  background: #e2e8f0;
}
.badge.warn { background: #feebc8; color: #975a16; }
.badge.ok { background: #c6f6d5; color: #276749; }
.badge.err { background: #fed7d7; color: #9b2c2c; }
.panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.pager { margin-top: 12px; display: flex; gap: 8px; align-items: center; }
</style>
