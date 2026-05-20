<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户管理</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0;
            background: #f8fafb;
            color: #1a2e2e;
        }
        .header {
            background: #0d9488;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { font-size: 1.2rem; }
        .header a {
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            border-radius: 6px;
        }
        .container {
            max-width: 900px;
            margin: 30px auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            overflow: hidden;
        }
        .toolbar {
            padding: 20px;
            border-bottom: 1px solid #e2e8e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .toolbar h2 { font-size: 1.1rem; color: #1a2e2e; }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-primary { background: #0d9488; color: white; }
        .btn-primary:hover { background: #0f766e; }
        .btn-danger { background: #e11d48; color: white; }
        .btn-danger:hover { background: #be123c; }
        .btn-secondary { background: #9ca3af; color: white; }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 14px 20px;
            text-align: left;
            border-bottom: 1px solid #e2e8e6;
        }
        th {
            background: #f8fafb;
            font-weight: 600;
            color: #4a5e5e;
            font-size: 13px;
            text-transform: uppercase;
        }
        tr:hover { background: #f8fafb; }
        .role-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .role-admin { background: #fef3c7; color: #92400e; }
        .role-operator { background: #dbeafe; color: #1e40af; }
        .role-viewer { background: #e5e7eb; color: #374151; }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
        }
        .modal-content {
            background: white;
            margin: 10% auto;
            padding: 25px;
            border-radius: 12px;
            max-width: 450px;
            width: 90%;
        }
        .modal h2 {
            margin-bottom: 20px;
            font-size: 1.1rem;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: #374151;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 14px;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #0d9488;
            box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.1);
        }
        .modal-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
        }
        .close {
            float: right;
            font-size: 24px;
            cursor: pointer;
            color: #9ca3af;
        }
        .close:hover { color: #374151; }
        .error { color: #e11d48; font-size: 13px; margin-top: 5px; }
        .success { color: #059669; font-size: 13px; margin-top: 5px; }
        .loading {
            text-align: center;
            padding: 40px;
            color: #9ca3af;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>用户管理</h1>
        <a href="/">返回首页</a>
    </div>

    <div class="container">
        <div class="toolbar">
            <h2>用户列表</h2>
            <button class="btn btn-primary" onclick="openCreateModal()">+ 新建用户</button>
        </div>

        <div id="loading" class="loading">加载中...</div>
        <table id="userTable" style="display: none;">
            <thead>
                <tr>
                    <th>用户名</th>
                    <th>角色</th>
                    <th>创建时间</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody id="userBody"></tbody>
        </table>
    </div>

    <!-- 创建用户模态框 -->
    <div id="createModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('createModal')">&times;</span>
            <h2>新建用户</h2>
            <form id="createForm">
                <div class="form-group">
                    <label>用户名</label>
                    <input type="text" name="username" required minlength="3">
                </div>
                <div class="form-group">
                    <label>密码</label>
                    <input type="password" name="password" required minlength="6">
                </div>
                <div class="form-group">
                    <label>角色</label>
                    <select name="role">
                        <option value="viewer">查看者 (viewer)</option>
                        <option value="operator">操作员 (operator)</option>
                        <option value="admin">管理员 (admin)</option>
                    </select>
                </div>
                <div id="createError" class="error" style="display: none;"></div>
                <div class="modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal('createModal')">取消</button>
                    <button type="submit" class="btn btn-primary">创建</button>
                </div>
            </form>
        </div>
    </div>

    <!-- 编辑用户模态框 -->
    <div id="editModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('editModal')">&times;</span>
            <h2>编辑用户</h2>
            <form id="editForm">
                <input type="hidden" name="user_id" id="editUserId">
                <div class="form-group">
                    <label>用户名</label>
                    <input type="text" id="editUsername" readonly style="background: #f3f4f6;">
                </div>
                <div class="form-group">
                    <label>新密码 (留空则不修改)</label>
                    <input type="password" name="password" minlength="6">
                </div>
                <div class="form-group">
                    <label>角色</label>
                    <select name="role" id="editRole">
                        <option value="viewer">查看者 (viewer)</option>
                        <option value="operator">操作员 (operator)</option>
                        <option value="admin">管理员 (admin)</option>
                    </select>
                </div>
                <div id="editError" class="error" style="display: none;"></div>
                <div class="modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeModal('editModal')">取消</button>
                    <button type="submit" class="btn btn-primary">保存</button>
                </div>
            </form>
        </div>
    </div>

    <!-- 删除确认模态框 -->
    <div id="deleteModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('deleteModal')">&times;</span>
            <h2>确认删除</h2>
            <p id="deleteMessage" style="margin: 15px 0; color: #374151;"></p>
            <div id="deleteError" class="error" style="display: none;"></div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal('deleteModal')">取消</button>
                <button type="button" class="btn btn-danger" onclick="confirmDelete()">删除</button>
            </div>
        </div>
    </div>

    <script>
        let currentUser = null;
        let deleteUserId = null;

        // 获取当前用户信息
        fetch('/api/auth/current_user')
            .then(r => r.json())
            .then(data => {
                if (!data.authenticated || data.user.role !== 'admin') {
                    alert('只有管理员可以访问此页面');
                    window.location.href = '/';
                    return;
                }
                currentUser = data.user;
                loadUsers();
            });

        function loadUsers() {
            fetch('/api/auth/users')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('userTable').style.display = 'table';

                    const tbody = document.getElementById('userBody');
                    tbody.innerHTML = '';

                    data.users.forEach(user => {
                        const roleClass = 'role-' + user.role;
                        const roleText = {
                            'admin': '管理员',
                            'operator': '操作员',
                            'viewer': '查看者'
                        }[user.role] || user.role;

                        const isSelf = currentUser && user.username === currentUser.username;
                        const actions = isSelf
                            ? '<span style="color: #9ca3af;">当前用户</span>'
                            : `<button class="btn btn-secondary" onclick="openEditModal(${user.id}, '${user.username}', '${user.role}')">编辑</button>
                               <button class="btn btn-danger" onclick="openDeleteModal(${user.id}, '${user.username}')">删除</button>`;

                        tbody.innerHTML += `
                            <tr>
                                <td>${user.username}</td>
                                <td><span class="role-badge ${roleClass}">${roleText}</span></td>
                                <td>${user.created_at || '-'}</td>
                                <td>${actions}</td>
                            </tr>
                        `;
                    });
                })
                .catch(err => {
                    document.getElementById('loading').textContent = '加载失败: ' + err;
                });
        }

        function openCreateModal() {
            document.getElementById('createForm').reset();
            document.getElementById('createError').style.display = 'none';
            document.getElementById('createModal').style.display = 'block';
        }

        function openEditModal(userId, username, role) {
            document.getElementById('editUserId').value = userId;
            document.getElementById('editUsername').value = username;
            document.getElementById('editRole').value = role;
            document.getElementById('editForm').querySelector('input[name="password"]').value = '';
            document.getElementById('editError').style.display = 'none';
            document.getElementById('editModal').style.display = 'block';
        }

        function openDeleteModal(userId, username) {
            deleteUserId = userId;
            document.getElementById('deleteMessage').textContent = `确定要删除用户 "${username}" 吗？此操作无法撤销。`;
            document.getElementById('deleteError').style.display = 'none';
            document.getElementById('deleteModal').style.display = 'block';
        }

        function closeModal(id) {
            document.getElementById(id).style.display = 'none';
        }

        // 创建用户
        document.getElementById('createForm').onsubmit = function(e) {
            e.preventDefault();
            const form = new FormData(this);
            const errorEl = document.getElementById('createError');

            fetch('/api/auth/users', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: form.get('username'),
                    password: form.get('password'),
                    role: form.get('role')
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    closeModal('createModal');
                    loadUsers();
                } else {
                    errorEl.textContent = data.error || '创建失败';
                    errorEl.style.display = 'block';
                }
            })
            .catch(err => {
                errorEl.textContent = '请求失败: ' + err;
                errorEl.style.display = 'block';
            });
        };

        // 编辑用户
        document.getElementById('editForm').onsubmit = function(e) {
            e.preventDefault();
            const form = new FormData(this);
            const userId = form.get('user_id');
            const password = form.get('password');
            const role = form.get('role');
            const errorEl = document.getElementById('editError');

            const body = {};
            if (password) body.password = password;
            if (role) body.role = role;

            fetch(`/api/auth/users/${userId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(body)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    closeModal('editModal');
                    loadUsers();
                } else {
                    errorEl.textContent = data.error || '更新失败';
                    errorEl.style.display = 'block';
                }
            })
            .catch(err => {
                errorEl.textContent = '请求失败: ' + err;
                errorEl.style.display = 'block';
            });
        };

        function confirmDelete() {
            const errorEl = document.getElementById('deleteError');

            fetch(`/api/auth/users/${deleteUserId}`, {
                method: 'DELETE'
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    closeModal('deleteModal');
                    loadUsers();
                } else {
                    errorEl.textContent = data.error || '删除失败';
                    errorEl.style.display = 'block';
                }
            })
            .catch(err => {
                errorEl.textContent = '请求失败: ' + err;
                errorEl.style.display = 'block';
            });
        }

        // 点击模态框外部关闭
        window.onclick = function(e) {
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        };
    </script>
</body>
</html>
