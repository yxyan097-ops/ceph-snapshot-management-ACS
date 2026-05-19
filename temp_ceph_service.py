"""Ceph service for RBD snapshot operations via SSH."""
import time
import tempfile
import os
from typing import List, Optional, Dict
from dataclasses import dataclass

import paramiko

from ceph_snapshot_manager.config.settings import CephConfig


@dataclass
class OperationResult:
    """Result of a snapshot operation."""
    success: bool
    output: str = ''
    error: str = ''
    commands: List[str] = None

    def __post_init__(self):
        if self.commands is None:
            self.commands = []

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'output': self.output,
            'error': self.error,
            'commands': self.commands
        }


@dataclass
class CleanupResult(OperationResult):
    """Result of a cleanup operation."""
    dry_run: bool = False

    def to_dict(self) -> dict:
        result = super().to_dict()
        result['dry_run'] = self.dry_run
        return result


@dataclass
class HealthStatus:
    """Ceph cluster health status."""
    healthy: bool
    status: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'healthy': self.healthy,
            'status': self.status,
            'error': self.error
        }


class CephService:
    """Ceph RBD snapshot operations via SSH."""

    def __init__(self, config: CephConfig):
        self.ssh_host = config.ssh_host
        self.ssh_user = config.ssh_user
        self.ssh_password = config.ssh_password
        self.ssh_key_path = config.ssh_key_path
        self.ssh_private_key = config.ssh_private_key
        self.snap_trim_script = config.snap_trim_script
        self.default_keep = config.default_keep
        self.client = None
        self._snapshot_count_cache = None
        self._snapshot_count_cache_time = 0
        self._cache_ttl = 30  # Cache TTL in seconds
        self._temp_key_file = None

    def _connect(self) -> None:
        """Establish SSH connection."""
        if self.client is None or self.client.get_transport() is None or not self.client.get_transport().is_active():
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            connect_kwargs = {
                'hostname': self.ssh_host,
                'username': self.ssh_user,
                'timeout': 30,
                'banner_timeout': 30,
                'auth_timeout': 30
            }
            if self.ssh_password:
                connect_kwargs['password'] = self.ssh_password
            elif self.ssh_private_key:
                # Write private key to temp file and use it
                self._temp_key_file = tempfile.NamedTemporaryFile(mode='w', suffix='_rsa', delete=False)
                self._temp_key_file.write(self.ssh_private_key)
                self._temp_key_file.close()
                os.chmod(self._temp_key_file.name, 0o600)
                connect_kwargs['key_filename'] = self._temp_key_file.name
            elif self.ssh_key_path:
                connect_kwargs['key_filename'] = self.ssh_key_path
            try:
                self.client.connect(**connect_kwargs)
            except paramiko.SSHException as e:
                self.client = None
                self._cleanup_temp_key()
                raise Exception(f"SSH连接失败: {str(e)}")
            except Exception as e:
                self.client = None
                self._cleanup_temp_key()
                raise Exception(f"无法连接到 {self.ssh_host}: {str(e)}")

    def _cleanup_temp_key(self) -> None:
        """Clean up temporary key file if it exists."""
        if self._temp_key_file:
            try:
                os.unlink(self._temp_key_file.name)
            except:
                pass
            self._temp_key_file = None

    def _disconnect(self) -> None:
        """Close SSH connection."""
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None
        self._cleanup_temp_key()

    def _exec_command(self, command: str, retry: int = 2) -> tuple:
        """Execute command via SSH with retry logic.

        Returns:
            tuple: (exit_status, stdout, stderr)
        """
        last_error = None
        for attempt in range(retry):
            try:
                self._connect()
                stdin, stdout, stderr = self.client.exec_command(command, get_pty=True)
                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode()
                error = stderr.read().decode()
                return exit_status, output, error
            except Exception as e:
                last_error = str(e)
                self._disconnect()
        raise Exception(f"执行命令失败: {last_error}")

    def _invalidate_cache(self) -> None:
        """Invalidate the snapshot count cache."""
        self._snapshot_count_cache = None

    # ==================== Pool Operations ====================

    def list_pools(self) -> List[str]:
        """List all Ceph pools."""
        cmd = "ceph osd pool ls"
        exit_status, stdout, stderr = self._exec_command(cmd)
        if exit_status != 0:
            raise Exception(f"Failed to list pools: {stderr}")
        return [p.strip() for p in stdout.strip().split('\n') if p.strip()]

    def list_volumes(self, pool: str) -> List[str]:
        """List RBD images in a pool."""
        cmd = f"rbd ls -p {pool} --format json"
        exit_status, stdout, stderr = self._exec_command(cmd)
        if exit_status != 0:
            return []
        try:
            import json
            return json.loads(stdout)
        except:
            return []

    def find_volume_pool(self, volume_id: str) -> Optional[str]:
        """Find which pool contains a specific volume."""
        pools = self.list_pools()
        for pool in pools:
            cmd = f"rbd info -p {pool} {volume_id} 2>/dev/null"
            exit_status, stdout, stderr = self._exec_command(cmd)
            if exit_status == 0:
                return pool
        return None

    # ==================== Snapshot Operations ====================

    def list_snapshots(self, pool: str, volume_name: str) -> List[dict]:
        """List snapshots for a volume."""
        cmd = f"rbd snap ls -p {pool} {volume_name} --format json"
        exit_status, stdout, stderr = self._exec_command(cmd)
        if exit_status != 0:
            return []
        try:
            import json
            return json.loads(stdout)
        except:
            return []

    def get_volume_snapshots(self, volume_id: str) -> List[dict]:
        """Get all snapshots for a volume by finding its pool first."""
        pool = self.find_volume_pool(volume_id)
        if not pool:
            return []
        return self.list_snapshots(pool, volume_id)

    def delete_snapshot(self, volume_id: str, snapshot_name: str, dry_run: bool = True) -> OperationResult:
        """Delete a specific snapshot.

        Args:
            volume_id: The RBD volume ID
            snapshot_name: Name of the snapshot to delete
            dry_run: If True, only return command without executing
        """
        pool = self.find_volume_pool(volume_id)
        if not pool:
            return OperationResult(success=False, error='Volume not found in any pool')

        snap_id = f'{pool}/{volume_id}@{snapshot_name}'
        cmd = f"rbd snap rm {snap_id}"

        # Check if this is the last unprotected snapshot
        all_snapshots = self.list_snapshots(pool, volume_id)
        unprotected_snapshots = [s for s in all_snapshots if s.get('protected') != 'true']
        is_last_snapshot = len(unprotected_snapshots) <= 1

        if dry_run:
            return OperationResult(
                success=True,
                output=f'[Dry Run] {cmd}',
                commands=[cmd],
                error='' if not is_last_snapshot else f'警告: 这将为卷的最后一个快照!'
            )

        # Check cluster health before delete
        can_proceed, proceed_msg = self.check_can_proceed()
        if not can_proceed:
            return OperationResult(
                success=False,
                error=f'集群状态不允许: {proceed_msg}',
                commands=[]
            )

        # Execute via user's script (which handles validation and PG status checks)
        script_cmd = f"{self.snap_trim_script} --disk-id {volume_id} --snap-name {snapshot_name}"
        exit_status, stdout, stderr = self._exec_command(script_cmd)

        if exit_status != 0:
            self._invalidate_cache()
            return OperationResult(
                success=False,
                output='',
                error=stderr,
                commands=[cmd]
            )

        # Wait for PGs to be active+clean after delete
        wait_cmd = 'while ! ceph -s 2>/dev/null | grep -q "active+clean"; do echo "等待 PG 恢复..."; sleep 5; done'
        self._exec_command(wait_cmd)

        self._invalidate_cache()

        warning = f'警告: 这将为卷的最后一个快照!' if is_last_snapshot else ''
        return OperationResult(
            success=True,
            output=stdout,
            error=warning,
            commands=[cmd]
        )

    def protect_snapshot(self, volume_id: str, snapshot_name: str) -> OperationResult:
        """Protect a snapshot to prevent deletion.

        Args:
            volume_id: The RBD volume ID
            snapshot_name: Name of the snapshot to protect

        Returns:
            OperationResult with success status
        """
        pool = self.find_volume_pool(volume_id)
        if not pool:
            return OperationResult(success=False, error='Volume not found in any pool')

        snap_id = f'{pool}/{volume_id}@{snapshot_name}'
        cmd = f"rbd snap protect {snap_id}"

        exit_status, stdout, stderr = self._exec_command(cmd)

        return OperationResult(
            success=exit_status == 0,
            output=stdout if exit_status == 0 else '',
            error=stderr if exit_status != 0 else ''
        )

    def unprotect_snapshot(self, volume_id: str, snapshot_name: str) -> OperationResult:
        """Unprotect a snapshot to allow deletion.

        Args:
            volume_id: The RBD volume ID
            snapshot_name: Name of the snapshot to unprotect

        Returns:
            OperationResult with success status
        """
        pool = self.find_volume_pool(volume_id)
        if not pool:
            return OperationResult(success=False, error='Volume not found in any pool')

        snap_id = f'{pool}/{volume_id}@{snapshot_name}'
        cmd = f"rbd snap unprotect {snap_id}"

        exit_status, stdout, stderr = self._exec_command(cmd)

        return OperationResult(
            success=exit_status == 0,
            output=stdout if exit_status == 0 else '',
            error=stderr if exit_status != 0 else ''
        )

    def create_snapshot(self, volume_id: str, snapshot_name: str) -> OperationResult:
        """Create a new snapshot."""
        pool = self.find_volume_pool(volume_id)
        if not pool:
            return OperationResult(success=False, error='卷未找到')

        snap_id = f'{pool}/{volume_id}@{snapshot_name}'
        cmd = f"rbd snap create {snap_id}"

        time.sleep(3)  # Delay 3 seconds before creation

        exit_status, stdout, stderr = self._exec_command(cmd)
        self._invalidate_cache()

        return OperationResult(
            success=exit_status == 0,
            output=stdout,
            error=stderr
        )

    def cleanup_snapshots(self, disk_id: str, keep_count: Optional[int] = None, dry_run: bool = True) -> CleanupResult:
        """Cleanup old snapshots, preserving the newest N.

        Args:
            disk_id: The RBD volume ID
            keep_count: Number of newest snapshots to keep (None uses default)
            dry_run: If True, only return commands without executing

        Returns:
            CleanupResult with commands and execution status
        """
        output_parts = []

        if keep_count is None:
            keep_count = self.default_keep

        output_parts.append(f'[步骤1] 查找卷所在存储池: disk_id={disk_id}')
        pool = self.find_volume_pool(disk_id)
        if not pool:
            return CleanupResult(success=False, error=f'卷 {disk_id} 未找到存储池', dry_run=dry_run, output='\n'.join(output_parts))
        output_parts.append(f'[步骤2] 找到存储池: {pool}')

        output_parts.append(f'[步骤3] 获取快照列表...')
        snapshots = self.list_snapshots(pool, disk_id)
        output_parts.append(f'      快照总数: {len(snapshots)}')
        if not snapshots:
            output_parts.append('[完成] 没有快照')
            return CleanupResult(success=True, output='\n'.join(output_parts), dry_run=dry_run)

        # Filter out protected snapshots (consistent with original script)
        valid_snapshots = [s for s in snapshots if s.get('protected') != 'true']
        output_parts.append(f'[步骤4] 过滤已保护快照: {len(snapshots)} -> {len(valid_snapshots)} (排除 {len(snapshots) - len(valid_snapshots)} 个已保护)')
        if not valid_snapshots:
            output_parts.append('[完成] 没有可清理的快照（全部已保护）')
            return CleanupResult(success=True, output='\n'.join(output_parts), dry_run=dry_run)

        # Sort by timestamp (oldest first)
        valid_snapshots.sort(key=lambda x: x.get('timestamp', ''))
        output_parts.append(f'[步骤5] 按时间排序 (最旧优先)')

        # Keep newest N, delete older ones
        to_delete = valid_snapshots[:-keep_count] if keep_count > 0 else valid_snapshots
        to_keep = valid_snapshots[-keep_count:] if keep_count > 0 else []
        output_parts.append(f'[步骤6] 保留策略: 保留最新 {keep_count} 个')
        output_parts.append(f'      将删除: {len(to_delete)} 个')
        output_parts.append(f'      将保留: {len(to_keep)} 个')

        if not to_delete:
            output_parts.append('[完成] 无需删除')
            return CleanupResult(success=True, output='\n'.join(output_parts), dry_run=dry_run)

        # Build command list for audit
        commands = [f"rbd snap rm {pool}/{disk_id}@{s['name']}" for s in to_delete]
        command_str = ' && '.join(commands)

        output_parts.append(f'[步骤7] 待删除快照:')
        for i, s in enumerate(to_delete, 1):
            output_parts.append(f'      {i}. {s["name"]}')
        output_parts.append(f'[步骤8] 构建删除命令...')

        if dry_run:
            output_parts.append(f'[Dry Run] 预览模式，不执行实际删除')
            output_parts.append(f'      命令: {command_str}')
            return CleanupResult(
                success=True,
                output='\n'.join(output_parts),
                commands=commands,
                dry_run=True
            )

        # Health check before execution
        can_proceed, proceed_msg = self.check_can_proceed()
        if not can_proceed:
            output_parts.append(f'[失败] 集群状态不允许: {proceed_msg}')
            return CleanupResult(
                success=False,
                output='\n'.join(output_parts),
                error=f'集群状态不允许: {proceed_msg}',
                dry_run=False
            )

        # Actually execute via the user's script (which handles PG status checks)
        keep_flag = "--keep"
        dry_flag = "--dry-run" if dry_run else ""

        disk_file = f"/tmp/disk_ids_{disk_id}.txt"
        script_cmd = f"echo '{disk_id}' > {disk_file} && {self.snap_trim_script} {dry_flag} {keep_flag} {keep_count} {disk_file} && rm -f {disk_file}"

        output_parts.append(f'[步骤9] 准备执行脚本...')
        output_parts.append(f'      脚本路径: {self.snap_trim_script}')
        output_parts.append(f'      参数: keep={keep_count}, disk_file={disk_file}')
        output_parts.append(f'[步骤10] 正在执行脚本...')

        exit_status, stdout, stderr = self._exec_command(script_cmd)
        self._invalidate_cache()

        output_parts.append(f'[步骤11] 脚本执行完成')
        output_parts.append(f'      退出状态: {exit_status}')

        if exit_status == 0:
            output_parts.append(f'[完成] 删除成功')
        else:
            output_parts.append(f'[失败] {stderr}')

        return CleanupResult(
            success=exit_status == 0,
            output='\n'.join(output_parts),
            error=stderr if exit_status != 0 else '',
            commands=[script_cmd],
            dry_run=False
        )

    # ==================== Snapshot Counts ====================

    def get_all_snapshot_counts(self) -> Dict[str, int]:
        """Get snapshot counts for all volumes with caching.

        Returns:
            dict: {volume_name: snapshot_count}
        """
        # Check cache validity
        if self._snapshot_count_cache is not None:
            if time.time() - self._snapshot_count_cache_time < self._cache_ttl:
                return self._snapshot_count_cache

        result = {}
        pool = 'rbd'
        cmd = f"for img in $(rbd ls -p {pool} 2>/dev/null); do count=$(rbd snap ls -p {pool} $img --format json 2>/dev/null | jq 'length' 2>/dev/null || echo 0); echo \"$img:$count\"; done"

        try:
            exit_status, stdout, stderr = self._exec_command(cmd)
            if exit_status != 0:
                return result
            for line in stdout.strip().split('\n'):
                if ':' in line:
                    img, count = line.strip().split(':', 1)
                    try:
                        result[img] = int(count)
                    except:
                        result[img] = 0
        except:
            pass

        # Update cache
        self._snapshot_count_cache = result
        self._snapshot_count_cache_time = time.time()
        return result

    # ==================== Health Check ====================

    # Blocking alerts that should prevent snapshot operations
    BLOCKING_ALERTS = [
        'PG_AVAILABILITY',   # PG 不可用
        'OSD_DISK_FULL',     # OSD 磁盘满
        'MON_DISK_FULL',     # MON 磁盘满
        'OSD_DOWN',          # OSD 宕机
        'MON_DOWN',          # MON 宕机
        'CLUSTER_DOWN',      # 集群宕机
    ]

    # Allowed warnings that should not block operations
    ALLOWED_WARNINGS = [
        'PG_NOT_DEEP_SCRUBBED',
        'PG_NOT_SCRUBBED',
        'DAEMON_OLD_VERSION',
        'NOSCRUB',
        'NODEEP_SCRUB',
    ]

    # PG states that should block operations
    BLOCKING_PG_STATES = [
        'peering',       # 正在协商
        'recovering',    # 正在恢复
        'backfilling',   # 正在回填
        'down',          # PG 宕机
        'incomplete',    # PG 不完整
        'stale',         # PG 陈旧
        'degraded',      # PG 降级
    ]

    def check_health(self) -> HealthStatus:
        """Check Ceph cluster health."""
        cmd = "ceph -s --format json"
        exit_status, stdout, stderr = self._exec_command(cmd)
        if exit_status != 0:
            return HealthStatus(healthy=False, error=stderr)

        try:
            import json
            status = json.loads(stdout)
            return HealthStatus(
                healthy=status.get('health', {}).get('status') == 'HEALTH_OK',
                status=status
            )
        except:
            return HealthStatus(healthy=False, error='Failed to parse ceph status')

    def check_can_proceed(self) -> tuple:
        """Check if snapshot operations can proceed.

        Returns:
            (can_proceed: bool, message: str)
            - can_proceed: True if operations can proceed
            - message: Status message describing the result
        """
        health_status = self.check_health()

        if not health_status.status:
            return False, health_status.error or "无法获取集群状态"

        status = health_status.status
        health = status.get('health', {})
        checks = health.get('checks', {})

        # 1. Check blocking alerts
        for alert in self.BLOCKING_ALERTS:
            if alert in checks:
                msg = checks[alert]['summary'].get('message', alert)
                return False, f"关键告警: {msg}"

        # 2. Check PG actual state
        pgmap = status.get('pgmap', {})
        pgs_by_state = pgmap.get('pgs_by_state', [])

        if pgs_by_state:
            total_pgs = 0
            blocking_states = []

            for pgs in pgs_by_state:
                count = pgs.get('count', 0)
                total_pgs += count
                state_name = pgs.get('state_name', '')

                # Check if any blocking state is present
                for blocking_state in self.BLOCKING_PG_STATES:
                    if blocking_state in state_name.lower():
                        blocking_states.append(f"{count} PG: {state_name}")
                        break

            if blocking_states:
                # Limit to first 3 blocking states for message
                msg = "; ".join(blocking_states[:3])
                return False, f"PG 状态异常: {msg}"

        # 3. Check if health status is not OK (but no blocking alerts)
        # This handles cases like HEALTH_WARN with only allowed warnings
        if health.get('status') != 'HEALTH_OK':
            # Check if there are any alerts not in allowed list
            active_alerts = [k for k in checks.keys() if k not in self.ALLOWED_WARNINGS]
            if active_alerts:
                return False, f"集群告警: {', '.join(active_alerts)}"

        return True, "OK"

    def close(self) -> None:
        """Close SSH connection."""
        self._disconnect()