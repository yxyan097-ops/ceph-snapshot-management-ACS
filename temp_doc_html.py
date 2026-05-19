<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>技术文档 - Ceph 快照管理</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f8fafb;
            color: #1a2e2e;
            line-height: 1.7;
        }
        .header {
            background: linear-gradient(135deg, #0d9488, #0f766e);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 8px rgba(13, 148, 136, 0.3);
        }
        .header h1 { font-size: 1.3rem; font-weight: 600; }
        .header a { color: white; text-decoration: none; padding: 10px 20px; background: rgba(255,255,255,0.2); border-radius: 6px; transition: background 0.2s; }
        .header a:hover { background: rgba(255,255,255,0.3); }
        .container { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
        .card {
            background: white;
            border-radius: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 30px;
            overflow: hidden;
        }
        .card-header {
            padding: 20px 25px;
            border-bottom: 1px solid #e2e8e6;
            background: linear-gradient(to right, #f8fafb, #ffffff);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-header h2 { font-size: 1.15rem; color: #1a2e2e; display: flex; align-items: center; gap: 10px; }
        .card-header h2::before { content: ''; display: inline-block; width: 4px; height: 20px; background: #0d9488; border-radius: 2px; }
        .badge { font-size: 11px; padding: 4px 10px; border-radius: 20px; background: #0d9488; color: white; font-weight: 500; }
        .card-body { padding: 25px; }
        h3 { font-size: 1rem; color: #0d9488; margin: 25px 0 12px 0; font-weight: 600; }
        h4 { font-size: 0.95rem; color: #1a2e2e; margin: 20px 0 10px 0; padding-left: 12px; border-left: 3px solid #ccfbf1; }
        p { margin-bottom: 12px; color: #4a5e5e; }
        .description { background: #f0fdfa; border-left: 4px solid #0d9488; padding: 15px 18px; border-radius: 0 8px 8px 0; margin: 15px 0; }
        .description strong { color: #0d9488; }
        .flow-container { display: flex; flex-direction: column; gap: 8px; margin: 20px 0; }
        .flow-step { display: flex; align-items: center; gap: 12px; }
        .flow-num { width: 28px; height: 28px; background: #0d9488; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; flex-shrink: 0; }
        .flow-text { color: #4a5e5e; }
        .code-block {
            background: #1e293b;
            color: #e2e8f0;
            padding: 18px;
            border-radius: 10px;
            overflow-x: auto;
            font-family: 'SF Mono', 'Fira Code', Monaco, monospace;
            font-size: 12.5px;
            line-height: 1.6;
            margin: 15px 0;
            border: 1px solid #334155;
        }
        .code-block .comment { color: #64748b; }
        .code-block .keyword { color: #c084fc; }
        .code-block .string { color: #86efac; }
        .code-block .function { color: #60a5fa; }
        .code-block .decorator { color: #fbbf24; }
        .code-block .class { color: #f472b6; }
        .code-block .number { color: #fb923c; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8e6; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #e2e8e6; }
        th { background: #f8fafb; font-weight: 600; color: #4a5e5e; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: #f8fafb; }
        .query-result { background: #1e293b; color: #86efac; border-radius: 8px; padding: 15px 18px; margin: 15px 0; font-family: monospace; font-size: 12.5px; line-height: 1.8; }
        .query-result .label { color: #60a5fa; }
        .query-result .header-row { color: #fbbf24; }
        .note { background: #fef3c7; border: 1px solid #fcd34d; border-radius: 8px; padding: 12px 15px; margin: 15px 0; font-size: 14px; }
        .note::before { content: '💡 '; }
        .nav { background: white; border-bottom: 1px solid #e2e8e6; padding: 0 30px; position: sticky; top: 0; z-index: 100; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .nav-list { display: flex; gap: 8px; list-style: none; overflow-x: auto; }
        .nav-list a { color: #4a5e5e; text-decoration: none; padding: 15px 16px; display: block; border-bottom: 2px solid transparent; white-space: nowrap; font-size: 14px; }
        .nav-list a:hover { color: #0d9488; }
        .nav-list a.active { color: #0d9488; border-bottom-color: #0d9488; }
        .toc { background: white; border-radius: 12px; padding: 20px 25px; margin-bottom: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
        .toc h4 { margin: 0 0 12px 0; padding-left: 0; border-left: none; color: #1a2e2e; font-size: 0.95rem; }
        .toc ul { list-style: none; display: flex; flex-wrap: wrap; gap: 8px; }
        .toc a { color: #0d9488; text-decoration: none; font-size: 14px; padding: 6px 12px; background: #f0fdfa; border-radius: 20px; }
        .toc a:hover { background: #ccfbf1; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Ceph 快照管理系统 - 技术文档</h1>
        <a href="/">返回首页</a>
    </div>

    <div class="nav">
        <ul class="nav-list">
            <li><a href="#auth">认证</a></li>
            <li><a href="#users">用户权限</a></li>
            <li><a href="#ssh">SSH密钥</a></li>
            <li><a href="#ceph">Ceph快照</a></li>
            <li><a href="#config">配置管理</a></li>
            <li><a href="#audit">审计日志</a></li>
        </ul>
    </div>

    <div class="container">
        <div class="toc">
            <h4>快速跳转</h4>
            <ul>
                <li><a href="#auth">认证模块</a></li>
                <li><a href="#users">用户权限</a></li>
                <li><a href="#ssh">SSH密钥</a></li>
                <li><a href="#ceph">Ceph快照</a></li>
                <li><a href="#config">配置管理</a></li>
                <li><a href="#audit">审计日志</a></li>
            </ul>
        </div>

        <!-- 认证模块 -->
        <div class="card" id="auth">
            <div class="card-header">
                <h2>1. 认证模块</h2>
                <span class="badge">核心模块</span>
            </div>
            <div class="card-body">
                <h3>1.1 用户登录</h3>
                <div class="description">
                    <strong>功能说明：</strong>用户通过用户名和密码登录系统。系统验证凭据后创建会话，后续请求通过会话Cookie识别用户身份。
                </div>
                <p><strong>实现方式：</strong>采用Flask-Login扩展管理用户会话。登录时验证bcrypt哈希密码，验证通过后调用login_user()创建会话。</p>
                <p><strong>会话存储：</strong>会话数据存储在服务器端，客户端只持有Cookie。登出时调用logout_user()销毁会话。</p>

                <h4>处理流程</h4>
                <div class="flow-container">
                    <div class="flow-step"><span class="flow-num">1</span><span class="flow-text">用户提交用户名和密码（JSON格式POST请求）</span></div>
                    <div class="flow-step"><span class="flow-num">2</span><span class="flow-text">从数据库根据用户名查找用户记录</span></div>
                    <div class="flow-step"><span class="flow-num">3</span><span class="flow-text">使用bcrypt验证密码哈希</span></div>
                    <div class="flow-step"><span class="flow-num">4</span><span class="flow-text">验证通过后调用login_user()创建Flask-Login会话</span></div>
                    <div class="flow-step"><span class="flow-num">5</span><span class="flow-text">返回成功响应，包含用户角色信息</span></div>
                </div>

                <h4>核心代码</h4>
                <div class="code-block">
<span class="comment"># 路由: POST /api/auth/login</span>
<span class="keyword">def</span> <span class="function">login</span>():
    data = request.get_json()
    username = data.get(<span class="string">'username'</span>, <span class="string">''</span>)
    password = data.get(<span class="string">'password'</span>, <span class="string">''</span>)

    <span class="comment"># 1. 查询用户</span>
    user = get_user_db().get_user(username)

    <span class="comment"># 2. 验证密码 (bcrypt)</span>
    <span class="keyword">if</span> user <span class="keyword">and</span> user.check_password(password):
        <span class="comment"># 3. 创建会话</span>
        login_user(user)
        <span class="keyword">return</span> jsonify({
            <span class="string">'success'</span>: <span class="keyword">True</span>,
            <span class="string">'user'</span>: {<span class="string">'username'</span>: user.username, <span class="string">'role'</span>: user.role}
        })

    <span class="comment"># 4. 验证失败</span>
    <span class="keyword">return</span> jsonify({<span class="string">'success'</span>: <span class="keyword">False</span>, <span class="string">'error'</span>: <span class="string">'用户名或密码错误'</span>}), <span class="string">401</span>
                </div>

                <h4>数据库验证</h4>
                <div class="query-result">
<span class="label">mysql></span> SELECT id, username, role, created_at FROM users;<br>
<span class="header-row">+----+----------+---------+---------------------+</span><br>
| id | username | role    | created_at          |<br>
<span class="header-row">+----+----------+---------+---------------------+</span><br>
|  1 | admin    | admin   | 2026-05-09 07:22:00|<br>
<span class="header-row">+----+----------+---------+---------------------+</span>
                </div>

                <h3>1.2 密码安全机制</h3>
                <div class="description">
                    <strong>功能说明：</strong>用户密码不以明文存储，使用bcrypt算法哈希后保存。bcrypt是专为密码设计的哈希算法，支持cost参数调整，具有防彩虹表攻击和可配置的计算强度。
                </div>
                <p><strong>哈希过程：</strong>明文密码 + 随机盐值 → bcrypt哈希。相同密码每次哈希结果不同，依赖盐值防止暴力破解。</p>
                <p><strong>验证过程：</strong>用户登录时，将输入密码与数据库中存储的哈希值比对，bcrypt会自动提取盐值重新计算比对。</p>

                <h4>代码实现</h4>
                <div class="code-block">
<span class="keyword">import</span> bcrypt

<span class="comment"># 密码哈希 (注册/修改时调用)</span>
<span class="keyword">def</span> <span class="function">hash_password</span>(password: str) -> str:
    <span class="comment"># bcrypt.gensalt() 生成随机盐, cost=12</span>
    <span class="keyword">return</span> bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

<span class="comment"># 密码验证 (登录时调用)</span>
<span class="keyword">def</span> <span class="function">check_password</span>(self, password: str) -> bool:
    <span class="comment"># 自动从哈希中提取盐值重新计算</span>
    <span class="keyword">return</span> bcrypt.checkpw(password.encode(), self.password_hash.encode())
                </div>
            </div>
        </div>

        <!-- 用户权限模块 -->
        <div class="card" id="users">
            <div class="card-header">
                <h2>2. 用户权限模块</h2>
                <span class="badge">核心模块</span>
            </div>
            <div class="card-body">
                <h3>2.1 角色权限体系</h3>
                <div class="description">
                    <strong>功能说明：</strong>系统采用RBAC（基于角色的访问控制）模型。定义三种角色，不同角色拥有不同操作权限，实现最小权限原则。
                </div>

                <table>
                    <tr><th>角色</th><th>角色说明</th><th>权限范围</th></tr>
                    <tr><td>admin</td><td>系统管理员</td><td>全部功能：用户管理、配置管理、密钥管理、快照操作、查看</td></tr>
                    <tr><td>operator</td><td>运维操作员</td><td>快照操作、查看（管理功能除外）</td></tr>
                    <tr><td>viewer</td><td>查看者</td><td>仅查看资源（不能执行任何操作）</td></tr>
                </table>

                <h3>2.2 权限检查机制</h3>
                <div class="description">
                    <strong>功能说明：</strong>每个用户对象拥有权限检查方法，路由处理器通过调用这些方法判断当前用户是否有权执行操作。
                </div>
                <p><strong>实现方式：</strong>User类实现权限方法，返回布尔值。路由入口处先检查@login_required确认已登录，再调用权限方法检查具体权限。</p>

                <h4>权限方法定义</h4>
                <div class="code-block">
<span class="keyword">class</span> <span class="class">User</span>(UserMixin):

    <span class="comment"># 是否可以执行快照清理操作</span>
    <span class="keyword">def</span> <span class="function">can_cleanup</span>(self) -> bool:
        <span class="keyword">return</span> self.role <span class="keyword">in</span> (<span class="string">'admin'</span>, <span class="string">'operator'</span>)

    <span class="comment"># 是否可以管理用户</span>
    <span class="keyword">def</span> <span class="function">can_manage_users</span>(self) -> bool:
        <span class="keyword">return</span> self.role == <span class="string">'admin'</span>

    <span class="comment"># 是否可以管理配置</span>
    <span class="keyword">def</span> <span class="function">can_manage_config</span>(self) -> bool:
        <span class="keyword">return</span> self.role == <span class="string">'admin'</span>

    <span class="comment"># 是否可以管理SSH密钥</span>
    <span class="keyword">def</span> <span class="function">can_manage_keys</span>(self) -> bool:
        <span class="keyword">return</span> self.role == <span class="string">'admin'</span>
                </div>

                <h3>2.3 用户管理功能</h3>
                <div class="description">
                    <strong>功能说明：</strong>管理员可以创建新用户、修改现有用户信息、删除不需要的用户账户。支持修改用户密码和角色。
                </div>
                <p><strong>约束条件：</strong>不能删除当前登录用户（防止无管理员情况）；不能修改自己的角色（防止权限失控）。</p>

                <h4>用户创建流程</h4>
                <div class="flow-container">
                    <div class="flow-step"><span class="flow-num">1</span><span class="flow-text">管理员填写用户名、密码、选择角色</span></div>
                    <div class="flow-step"><span class="flow-num">2</span><span class="flow-text">服务端对密码进行bcrypt哈希</span></div>
                    <div class="flow-step"><span class="flow-num">3</span><span class="flow-text">写入users表（用户名唯一索引）</span></div>
                    <div class="flow-step"><span class="flow-num">4</span><span class="flow-text">返回创建成功</span></div>
                </div>

                <h4>用户删除代码</h4>
                <div class="code-block">
<span class="decorator">@auth_bp.route</span>(<span class="string">'/api/auth/users/&lt;int:user_id&gt;'</span>, methods=[<span class="string">'DELETE'</span>])
<span class="decorator">@login_required</span>
<span class="keyword">def</span> <span class="function">delete_user</span>(user_id):
    <span class="comment"># 权限检查</span>
    <span class="keyword">if not</span> current_user.can_manage_users():
        <span class="keyword">return</span> jsonify({<span class="string">'error'</span>: <span class="string">'权限不足'</span>}), <span class="string">403</span>

    <span class="comment"># 防止删除自己</span>
    <span class="keyword">if</span> user_id == current_user.id:
        <span class="keyword">return</span> jsonify({<span class="string">'error'</span>: <span class="string">'不能删除当前登录用户'</span>}), <span class="string">400</span>

    get_user_db().delete_user(user_id)
    <span class="keyword">return</span> jsonify({<span class="string">'success'</span>: <span class="keyword">True</span>})
                </div>
            </div>
        </div>

        <!-- SSH密钥模块 -->
        <div class="card" id="ssh">
            <div class="card-header">
                <h2>3. SSH密钥管理模块</h2>
                <span class="badge">核心模块</span>
            </div>
            <div class="card-body">
                <h3>3.1 密钥上传与管理</h3>
                <div class="description">
                    <strong>功能说明：</strong>管理员上传SSH私钥文件，系统自动解析生成公钥和指纹，关联到指定Zone后用于SSH连接Ceph节点。
                </div>
                <p><strong>密钥格式支持：</strong>系统使用cryptography库解析OpenSSH格式私钥，支持RSA、ED25519、ECDSA等类型。</p>
                <p><strong>指纹计算：</strong>使用MD5哈希DER编码的公钥，格式化为冒号分隔的十六进制字符串（如AA:BB:CC:DD...）。</p>

                <h4>处理流程</h4>
                <div class="flow-container">
                    <div class="flow-step"><span class="flow-num">1</span><span class="flow-text">管理员粘贴私钥内容，填写Zone信息</span></div>
                    <div class="flow-step"><span class="flow-num">2</span><span class="flow-text">cryptography库解析私钥，提取公钥</span></div>
                    <div class="flow-step"><span class="flow-num">3</span><span class="flow-text">计算MD5指纹用于标识</span></div>
                    <div class="flow-step"><span class="flow-num">4</span><span class="flow-text">私钥、公钥、指纹存入MySQL</span></div>
                    <div class="flow-step"><span class="flow-num">5</span><span class="flow-text">返回公钥和指纹供确认</span></div>
                </div>

                <h4>密钥解析代码</h4>
                <div class="code-block">
<span class="comment"># 使用cryptography库解析OpenSSH格式私钥</span>
<span class="keyword">from</span> cryptography.hazmat.primitives <span class="keyword">import</span> serialization

<span class="keyword">def</span> <span class="function">load_key_and_get_info</span>(private_key_str):
    <span class="comment"># 解析私钥（自动识别RSA/ED25519/EC类型）</span>
    key = serialization.load_ssh_private_key(
        private_key_str.encode(),
        password=<span class="keyword">None</span>
    )
    pub = key.public_key()

    <span class="comment"># 生成OpenSSH格式公钥</span>
    pub_bytes = pub.public_bytes(
        serialization.Encoding.OpenSSH,
        serialization.PublicFormat.OpenSSH
    )

    <span class="comment"># 计算MD5指纹</span>
    der = pub.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo
    )
    md5hash = hashlib.md5(der)
    fingerprint = <span class="string">':'</span>.join(a+b <span class="keyword">for</span> a,b <span class="keyword">in</span>
        <span class="function">zip</span>(md5hash.hexdigest()[::<span class="string">2</span>], md5hash.hexdigest()[<span class="string">1</span>::<span class="string">2</span>]))

    <span class="keyword">return</span> public_key, fingerprint
                </div>

                <h3>3.2 SSH连接认证</h3>
                <div class="description">
                    <strong>功能说明：</strong>连接Ceph节点时，使用数据库中存储的私钥进行SSH认证。系统将私钥写入临时文件，设置正确权限后使用Paramiko连接。
                </div>
                <p><strong>临时文件安全：</strong>私钥写入临时文件后立即设置600权限（仅所有者读写），SSH连接完成后自动删除临时文件。</p>
                <p><strong>连接复用：</strong>维护SSH连接池，已建立的连接在活跃状态下会复用，避免频繁建立连接开销。</p>

                <h4>连接代码</h4>
                <div class="code-block">
<span class="keyword">def</span> <span class="function">_connect</span>(self):
    <span class="comment"># 检查现有连接是否活跃</span>
    <span class="keyword">if</span> self.client <span class="keyword">and</span> self.client.get_transport().is_active():
        <span class="keyword">return</span>

    <span class="comment"># 私钥写入临时文件</span>
    self._temp_key_file = tempfile.NamedTemporaryFile(
        mode=<span class="string">'w'</span>, suffix=<span class="string">'_rsa'</span>, delete=<span class="keyword">False</span>
    )
    self._temp_key_file.write(self.ssh_private_key)
    self._temp_key_file.close()

    <span class="comment"># 设置权限600 (仅所有者可读写)</span>
    os.chmod(self._temp_key_file.name, <span class="string">0o600</span>)

    <span class="comment"># Paramiko SSH连接</span>
    self.client = paramiko.SSHClient()
    self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    self.client.connect(
        hostname=self.ssh_host,
        username=self.ssh_user,
        key_filename=self._temp_key_file.name,
        timeout=<span class="string">30</span>
    )
                </div>

                <div class="note">连接完成后在_disconnect()或_cleanup_temp_key()中删除临时文件，确保私钥不留存。</div>

                <h3>3.3 密钥存储结构</h3>
                <div class="query-result">
<span class="label">mysql></span> SELECT zone_id, zone_name, ssh_user, fingerprint, LENGTH(private_key) as pk_len FROM zone_keys;<br>
<span class="header-row">+---------+-------------+----------+-------------------------------+-------+</span><br>
| zone_id | zone_name   | ssh_user | fingerprint                  |pk_len |<br>
<span class="header-row">+---------+-------------+----------+-------------------------------+-------+</span><br>
| zone    | 172.16.100.3| root     | 1c:e7:1b:25:14:a6:99:ed:... | 3380  |<br>
<span class="header-row">+---------+-------------+----------+-------------------------------+-------+</span>
                </div>
            </div>
        </div>

        <!-- Ceph快照模块 -->
        <div class="card" id="ceph">
            <div class="card-header">
                <h2>4. Ceph快照操作模块</h2>
                <span class="badge">核心模块</span>
            </div>
            <div class="card-body">
                <h3>4.1 卷与快照查询</h3>
                <div class="description">
                    <strong>功能说明：</strong>通过SSH连接到Ceph节点，执行rbd命令查询存储池、卷和快照信息。支持列出所有存储池、池内卷、卷的快照列表。
                </div>
                <p><strong>命令执行：</strong>使用Paramiko执行远程命令，通过exec_command()获取stdout/stderr输出，解析JSON格式结果。</p>
                <p><strong>数据缓存：</strong>快照计数结果缓存30秒，减少频繁SSH查询。</p>

                <table>
                    <tr><th>操作</th><th>ceph命令</th><th>说明</th></tr>
                    <tr><td>list_pools</td><td>ceph osd pool ls</td><td>列出所有存储池名称</td></tr>
                    <tr><td>list_volumes</td><td>rbd ls -p {pool} --format json</td><td>列出指定池内所有卷</td></tr>
                    <tr><td>list_snapshots</td><td>rbd snap ls -p {pool} {vol} --format json</td><td>列出卷的所有快照</td></tr>
                    <tr><td>find_volume_pool</td><td>rbd info -p {pool} {vol}</td><td>查询卷所在存储池</td></tr>
                </table>

                <h3>4.2 快照创建</h3>
                <div class="description">
                    <strong>功能说明：</strong>为指定卷创建新快照。快照命名格式为 pool/volume@snapshot-name。创建后等待3秒确保快照完全创建。
                </div>

                <h4>创建流程</h4>
                <div class="flow-container">
                    <div class="flow-step"><span class="flow-num">1</span><span class="flow-text">根据卷ID查找所在存储池</span></div>
                    <div class="flow-step"><span class="flow-num">2</span><span class="flow-text">构造快照ID: pool/volume@snapshot-name</span></div>
                    <div class="flow-step"><span class="flow-num">3</span><span class="flow-text">执行 rbd snap create 命令</span></div>
                    <div class="flow-step"><span class="flow-num">4</span><span class="flow-text">等待3秒确保快照创建完成</span></div>
                    <div class="flow-step"><span class="flow-num">5</span><span class="flow-text">使快照计数缓存失效</span></div>
                </div>

                <h4>代码实现</h4>
                <div class="code-block">
<span class="keyword">def</span> <span class="function">create_snapshot</span>(self, volume_id: str, snapshot_name: str) -> OperationResult:
    <span class="comment"># 查找卷所在池</span>
    pool = self.find_volume_pool(volume_id)
    <span class="keyword">if not</span> pool:
        <span class="keyword">return</span> OperationResult(success=<span class="keyword">False</span>, error=<span class="string">'卷未找到'</span>)

    <span class="comment"># 构造快照ID</span>
    snap_id = <span class="string">f'{pool}/{volume_id}@{snapshot_name}'</span>
    cmd = <span class="string">f"rbd snap create {snap_id}"</span>

    <span class="comment"># 创建前等待3秒</span>
    time.sleep(<span class="string">3</span>)

    <span class="comment"># 执行命令</span>
    exit_status, stdout, stderr = self._exec_command(cmd)
    self._invalidate_cache()

    <span class="keyword">return</span> OperationResult(
        success=exit_status == <span class="string">0</span>,
        output=stdout,
        error=stderr
    )
                </div>

                <h3>4.3 快照清理策略</h3>
                <div class="description">
                    <strong>功能说明：</strong>自动清理旧快照，保留最新N个。系统按时间戳排序快照，过滤已保护快照，确定要删除的快照后批量删除。
                </div>
                <p><strong>保留策略：</strong>默认保留3个快照（可配置）。按时间戳升序排列，删除除最后N个外的所有可删除快照。</p>
                <p><strong>保护快照：</strong>已通过rbd snap protect保护的快照不会被删除，防止重要快照被误删。</p>

                <h4>清理逻辑</h4>
                <div class="code-block">
<span class="keyword">def</span> <span class="function">cleanup_snapshots</span>(self, disk_id: str, keep_count: int = <span class="keyword">None</span>, dry_run: bool = <span class="keyword">True</span>):
    <span class="comment"># 1. 查找卷所在池</span>
    pool = self.find_volume_pool(disk_id)

    <span class="comment"># 2. 获取快照列表</span>
    snapshots = self.list_snapshots(pool, disk_id)

    <span class="comment"># 3. 过滤已保护快照 (不能删除)</span>
    valid_snapshots = [s <span class="keyword">for</span> s <span class="keyword">in</span> snapshots <span class="keyword">if</span> s.get(<span class="string">'protected'</span>) != <span class="string">'true'</span>]

    <span class="comment"># 4. 按时间戳排序 (最旧在前)</span>
    valid_snapshots.sort(key=<span class="keyword">lambda</span> x: x.get(<span class="string">'timestamp'</span>, <span class="string">''</span>))

    <span class="comment"># 5. 保留最新N个，N之前的要删除</span>
    to_delete = valid_snapshots[:-keep_count] <span class="keyword">if</span> keep_count > <span class="string">0</span> <span class="keyword">else</span> valid_snapshots
    to_keep = valid_snapshots[-keep_count:] <span class="keyword">if</span> keep_count > <span class="string">0</span> <span class="keyword">else</span> []

    <span class="comment"># 6. 干跑模式: 仅返回命令不执行</span>
    <span class="keyword">if</span> dry_run:
        commands = [<span class="string">f"rbd snap rm {pool}/{disk_id}@{s['name']}"</span> <span class="keyword">for</span> s <span class="keyword">in</span> to_delete]
        <span class="keyword">return</span> CleanupResult(success=<span class="keyword">True</span>, commands=commands, dry_run=<span class="keyword">True</span>)

    <span class="comment"># 7. 实际执行清理脚本</span>
    script_cmd = <span class="string">f"{self.snap_trim_script} --keep {keep_count} /tmp/disk_ids_{disk_id}.txt"</span>
    exit_status, stdout, stderr = self._exec_command(script_cmd)
                </div>

                <h3>4.4 集群健康检查</h3>
                <div class="description">
                    <strong>功能说明：</strong>执行快照操作前检查Ceph集群状态，阻止在集群不健康时执行操作。检查关键告警和PG状态。
                </div>

                <table>
                    <tr><th>告警类型</th><th>说明</th><th>影响</th></tr>
                    <tr><td>PG_AVAILABILITY</td><td>PG不可用</td><td>阻止操作</td></tr>
                    <tr><td>OSD_DISK_FULL</td><td>OSD磁盘满</td><td>阻止操作</td></tr>
                    <tr><td>OSD_DOWN</td><td>OSD宕机</td><td>阻止操作</td></tr>
                    <tr><td>MON_DOWN</td><td>MON宕机</td><td>阻止操作</td></tr>
                    <tr><td>PG_NOT_DEEP_SCRUBBED</td><td>PG未深度清洗</td><td>允许操作</td></tr>
                </table>

                <h4>检查代码</h4>
                <div class="code-block">
<span class="comment"># 阻止操作的告警</span>
BLOCKING_ALERTS = [<span class="string">'PG_AVAILABILITY'</span>, <span class="string">'OSD_DISK_FULL'</span>, <span class="string">'OSD_DOWN'</span>, <span class="string">'MON_DOWN'</span>]

<span class="comment"># 阻止操作的PG状态</span>
BLOCKING_PG_STATES = [<span class="string">'peering'</span>, <span class="string">'recovering'</span>, <span class="string">'backfilling'</span>,
                      <span class="string">'down'</span>, <span class="string">'incomplete'</span>, <span class="string">'stale'</span>, <span class="string">'degraded'</span>]

<span class="keyword">def</span> <span class="function">check_can_proceed</span>(self) -> tuple:
    status = self.check_health()
    <span class="keyword">if not</span> status.status:
        <span class="keyword">return False</span>, <span class="string">"无法获取集群状态"</span>

    <span class="comment"># 检查关键告警</span>
    <span class="keyword">for</span> alert <span class="keyword">in</span> self.BLOCKING_ALERTS:
        <span class="keyword">if</span> alert <span class="keyword">in</span> checks:
            <span class="keyword">return False</span>, <span class="string">f"关键告警: {checks[alert]['summary']['message']}"</span>

    <span class="comment"># 检查PG状态</span>
    <span class="keyword">for</span> pgs <span class="keyword">in</span> pgs_by_state:
        state_name = pgs.get(<span class="string">'state_name'</span>, <span class="string">''</span>)
        <span class="keyword">for</span> blocking <span class="keyword">in</span> self.BLOCKING_PG_STATES:
            <span class="keyword">if</span> blocking <span class="keyword">in</span> state_name.lower():
                <span class="keyword">return False</span>, <span class="string">f"PG状态异常: {state_name}"</span>

    <span class="keyword">return True</span>, <span class="string">"OK"</span>
                </div>
            </div>
        </div>

        <!-- 配置管理模块 -->
        <div class="card" id="config">
            <div class="card-header">
                <h2>5. 配置管理模块</h2>
                <span class="badge">核心模块</span>
            </div>
            <div class="card-body">
                <h3>5.1 配置存储机制</h3>
                <div class="description">
                    <strong>功能说明：</strong>应用配置集中存储在MySQL数据库，支持热更新无需重启应用。敏感配置（API密钥、密码）与普通配置分开存储和访问。
                </div>
                <p><strong>存储结构：</strong>key-value结构，is_secret字段标识是否敏感。敏感配置通过独立方法get_secret()访问，普通配置通过get()访问。</p>
                <p><strong>热更新：</strong>每次请求时从数据库加载配置，修改配置后立即生效，无需重启应用。</p>

                <table>
                    <tr><th>配置项</th><th>类型</th><th>说明</th></tr>
                    <tr><td>cloudstack_url</td><td>普通</td><td>CloudStack API地址</td></tr>
                    <tr><td>cloudstack_api_key</td><td>敏感</td><td>CloudStack API密钥</td></tr>
                    <tr><td>cloudstack_secret_key</td><td>敏感</td><td>CloudStack API密钥</td></tr>
                    <tr><td>snap_trim_script</td><td>普通</td><td>快照清理脚本路径</td></tr>
                    <tr><td>default_keep</td><td>普通</td><td>默认保留快照数</td></tr>
                    <tr><td>app_secret_key</td><td>敏感</td><td>Flask会话密钥</td></tr>
                </table>

                <h3>5.2 敏感信息保护</h3>
                <div class="description">
                    <strong>功能说明：</strong>敏感配置（API密钥、密码等）在数据库中通过is_secret字段标识。读取时get()方法对敏感配置返回None，强制使用get_secret()明确授权访问。
                </div>
                <p><strong>设计目的：</strong>防止敏感信息在日志或错误信息中泄露，明确区分敏感数据的访问路径。</p>

                <h4>代码实现</h4>
                <div class="code-block">
<span class="comment"># 普通配置获取 (敏感配置返回None)</span>
<span class="keyword">def</span> <span class="function">get</span>(self, key: str) -> Optional[str]:
    result = conn.execute(text(
        <span class="string">"SELECT config_value, is_secret FROM app_config WHERE config_key = :key"</span>
    ), {<span class="string">"key"</span>: key})
    row = result.fetchone()
    <span class="keyword">if</span> row[1]:  <span class="comment"># is_secret=True 时返回 None</span>
        <span class="keyword">return None</span>
    <span class="keyword">return</span> row[<span class="string">0</span>]

<span class="comment"># 敏感配置获取 (必须明确调用)</span>
<span class="keyword">def</span> <span class="function">get_secret</span>(self, key: str) -> Optional[str]:
    result = conn.execute(text(
        <span class="string">"SELECT config_value FROM app_config WHERE config_key=:key AND is_secret=TRUE"</span>
    ), {<span class="string">"key"</span>: key})
    row = result.fetchone()
    <span class="keyword">return</span> row[<span class="string">0</span>] <span class="keyword">if</span> row <span class="keyword">else None</span>
                </div>

                <h3>5.3 配置加载流程</h3>
                <div class="description">
                    <strong>功能说明：</strong>应用启动时和首次请求时从数据库加载完整配置，构建各服务实例。CloudStack和Ceph配置分别构建。
                </div>

                <div class="flow-container">
                    <div class="flow-step"><span class="flow-num">1</span><span class="flow-text">从环境变量读取DATABASE_URL</span></div>
                    <div class="flow-step"><span class="flow-num">2</span><span class="flow-text">连接MySQL数据库</span></div>
                    <div class="flow-step"><span class="flow-num">3</span><span class="flow-text">加载app_config表构建CloudStackConfig</span></div>
                    <div class="flow-step"><span class="flow-num">4</span><span class="flow-text">加载zone_keys表构建每个Zone的CephConfig</span></div>
                    <div class="flow-step"><span class="flow-num">5</span><span class="flow-text">构建各服务实例并绑定配置</span></div>
                </div>

                <h4>数据库验证</h4>
                <div class="query-result">
<span class="label">mysql></span> SELECT config_key, description, is_secret FROM app_config;<br>
<span class="header-row">+-------------+-------------------------------+-----------+</span><br>
| config_key  | description                   | is_secret |<br>
<span class="header-row">+-------------+-------------------------------+-----------+</span><br>
| cloudstack_url | CloudStack API URL          | 0         |<br>
| cloudstack_api_key | CloudStack API Key        | 1         |<br>
| cloudstack_secret_key | CloudStack Secret Key   | 1         |<br>
| snap_trim_script | Snapshot trim script path  | 0         |<br>
| default_keep | Default snapshot retention    | 0         |<br>
| app_secret_key | Flask secret key            | 1         |<br>
<span class="header-row">+-------------+-------------------------------+-----------+</span>
                </div>
            </div>
        </div>

        <!-- 审计日志模块 -->
        <div class="card" id="audit">
            <div class="card-header">
                <h2>6. 审计日志模块</h2>
                <span class="badge">核心模块</span>
            </div>
            <div class="card-body">
                <h3>6.1 审计日志功能</h3>
                <div class="description">
                    <strong>功能说明：</strong>记录所有快照操作到数据库，包括操作人、时间、动作类型、操作目标、执行结果、客户端IP等完整信息。支持日志查询和导出。
                </div>
                <p><strong>记录时机：</strong>每次快照操作（创建、删除、保护、取消保护、清理）执行后自动记录。</p>
                <p><strong>信息完整：</strong>记录实际操作使用的命令、返回结果、错误信息，方便问题排查和合规审计。</p>

                <table>
                    <tr><th>字段</th><th>说明</th></tr>
                    <tr><td>timestamp</td><td>操作时间</td></tr>
                    <tr><td>username</td><td>操作用户</td></tr>
                    <tr><td>action</td><td>操作类型(create/delete/protect/unprotect/cleanup)</td></tr>
                    <tr><td>zone_id</td><td>Zone标识</td></tr>
                    <tr><td>volume_id</td><td>卷ID</td></tr>
                    <tr><td>snapshot_name</td><td>快照名称</td></tr>
                    <tr><td>result</td><td>操作结果(success/failed)</td></tr>
                    <tr><td>message</td><td>返回消息/错误信息</td></tr>
                    <tr><td>commands</td><td>实际执行的命令</td></tr>
                    <tr><td>client_ip</td><td>客户端IP地址</td></tr>
                </table>

                <h3>6.2 记录机制</h3>
                <div class="description">
                    <strong>功能说明：</strong>SnapshotService封装CephService，在调用前后添加审计日志记录。获取当前用户从Flask-Login的current_user获取。
                </div>

                <h4>记录代码</h4>
                <div class="code-block">
<span class="keyword">class</span> <span class="class">SnapshotService</span>:
    <span class="keyword">def</span> <span class="function">delete_snapshot</span>(self, volume_id, snapshot_name, dry_run):
        <span class="comment"># 1. 执行实际删除操作</span>
        op_result = self.ceph_service.delete_snapshot(volume_id, snapshot_name, dry_run)

        <span class="comment"># 2. 记录审计日志</span>
        self._audit_log(
            action=<span class="string">'delete_snapshot'</span>,
            result=<span class="string">'success'</span> <span class="keyword">if</span> op_result.success <span class="keyword">else</span> <span class="string">'failed'</span>,
            volume_id=volume_id,
            snapshot_name=snapshot_name,
            dry_run=dry_run,
            message=op_result.error <span class="keyword">or</span> op_result.output,
            commands=<span class="string">'\n'</span>.join(op_result.commands)
        )

        <span class="keyword">return</span> op_result

    <span class="keyword">def</span> <span class="function">_audit_log</span>(self, action, result, **kwargs):
        audit_db.log(
            username=current_user.username,
            action=action,
            result=result,
            client_ip=request.remote_addr,
            **kwargs
        )
                </div>

                <h3>6.3 日志查询</h3>
                <div class="description">
                    <strong>功能说明：</strong>支持按时间范围、用户、操作类型等条件查询审计日志。审计页面展示最近操作记录。
                </div>

                <h4>最新日志查询结果</h4>
                <div class="query-result">
<span class="label">mysql></span> SELECT timestamp, username, action, result, LEFT(volume_id,20) as vol FROM audit_logs ORDER BY timestamp DESC LIMIT 3;<br>
<span class="header-row">+---------------------+----------+------------------+---------+----------------------+</span><br>
| timestamp           | username | action           | result  | vol                  |<br>
<span class="header-row">+---------------------+----------+------------------+---------+----------------------+</span><br>
| 2026-05-11 14:30:00| admin    | create_snapshot  | success | 4dc2c030-35fe-4294-|<br>
| 2026-05-11 14:25:00| admin    | cleanup_snapshots| success | 01a862f9-e035-4386-|<br>
| 2026-05-11 14:20:00| admin    | delete_snapshot  | success | 4dc2c030-35fe-4294-|<br>
<span class="header-row">+---------------------+----------+------------------+---------+----------------------+</span>
                </div>
            </div>
        </div>

    </div>

    <script>
        document.querySelectorAll('.nav-list a').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    document.querySelectorAll('.nav-list a').forEach(l => l.classList.remove('active'));
                    this.classList.add('active');
                }
            });
        });

        window.addEventListener('scroll', function() {
            const sections = document.querySelectorAll('.card[id]');
            let current = '';
            sections.forEach(section => {
                const rect = section.getBoundingClientRect();
                if (rect.top <= 120) {
                    current = section.getAttribute('id');
                }
            });
            document.querySelectorAll('.nav-list a').forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === '#' + current) {
                    link.classList.add('active');
                }
            });
        });
    </script>
</body>
</html>
