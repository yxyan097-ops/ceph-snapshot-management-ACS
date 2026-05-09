"""Snapshot orchestration service."""
from typing import List, Optional

from ceph_snapshot_manager.services.ceph_service import CephService, CleanupResult
from ceph_snapshot_manager.services.cloudstack_service import CloudStackService
from ceph_snapshot_manager.models.audit import AuditLogDB


class SnapshotService:
    """Orchestrates snapshot operations across Ceph and CloudStack."""

    def __init__(
        self,
        ceph_service: CephService,
        cloudstack_service: CloudStackService,
        audit_db: AuditLogDB
    ):
        self.ceph = ceph_service
        self.cloudstack = cloudstack_service
        self.audit = audit_db

    def get_zones(self) -> List[dict]:
        """Get all CloudStack zones."""
        return self.cloudstack.list_zones()

    def get_volumes_with_snapshot_counts(self, zone_id: str) -> List[dict]:
        """Get volumes with Ceph snapshot counts.

        Args:
            zone_id: CloudStack zone ID

        Returns:
            List of volumes with snapshot_count field added
        """
        volumes = self.cloudstack.list_volumes(zone_id)

        # Get all Ceph snapshot counts in one call
        snapshot_counts = self.ceph.get_all_snapshot_counts()

        # Map volume names to snapshot counts
        for vol in volumes:
            vol_id = vol['id']
            # RBD image name is the volume ID (UUID), not the CloudStack volume name
            vol['snapshot_count'] = snapshot_counts.get(vol_id, 0)

        return volumes

    def get_volume_snapshots(self, volume_id: str) -> List[dict]:
        """Get Ceph snapshots for a volume."""
        return self.ceph.get_volume_snapshots(volume_id)

    def get_cloudstack_snapshots(self, volume_id: str) -> List[dict]:
        """Get CloudStack snapshots for a volume."""
        return self.cloudstack.list_snapshots(volume_id=volume_id)

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        if request:
            return request.remote_addr or 'unknown'
        return 'unknown'

    def delete_snapshot(
        self,
        volume_id: str,
        snapshot_name: str,
        dry_run: bool = True,
        username: Optional[str] = None,
        zone_id: Optional[str] = None,
        zone_name: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> dict:
        """Delete a snapshot.

        Args:
            volume_id: The volume ID
            snapshot_name: Name of the snapshot to delete
            dry_run: If True, only preview without executing
            username: Username for audit log (optional)
            zone_id: Zone ID (optional)
            zone_name: Zone name (optional)
            client_ip: Client IP address (optional)

        Returns:
            Result dict with success, output, etc.
        """
        # Get Ceph pool info for audit
        pool = self.ceph.find_volume_pool(volume_id)
        full_snap_name = f"{pool}/{volume_id}@{snapshot_name}" if pool else f"{volume_id}@{snapshot_name}"
        command = f"rbd snap rm {full_snap_name}"

        result = self.ceph.delete_snapshot(volume_id, snapshot_name, dry_run=dry_run)

        # Add audit logging
        if username:
            self.audit.add_log(
                username=username,
                action='delete_snapshot',
                zone_id=zone_id,
                zone_name=zone_name,
                volume_id=volume_id,
                volume_name=volume_id,
                snapshot_name=snapshot_name,
                ceph_pool=pool,
                full_snapshot_name=full_snap_name,
                dry_run=dry_run,
                result='success' if result.success else 'failed',
                message=result.output or result.error,
                commands=command,
                client_ip=client_ip
            )

        return result.to_dict()

    def create_snapshot(
        self,
        volume_id: str,
        snapshot_name: str,
        username: Optional[str] = None,
        zone_id: Optional[str] = None,
        zone_name: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> dict:
        """Create a snapshot.

        Args:
            volume_id: The volume ID
            snapshot_name: Name for the new snapshot
            username: Username for audit log (optional)
            zone_id: Zone ID (optional)
            zone_name: Zone name (optional)
            client_ip: Client IP address (optional)

        Returns:
            Result dict with success, output, etc.
        """
        pool = self.ceph.find_volume_pool(volume_id)
        full_snap_name = f"{pool}/{volume_id}@{snapshot_name}" if pool else f"{volume_id}@{snapshot_name}"
        command = f"rbd snap create {full_snap_name}"

        result = self.ceph.create_snapshot(volume_id, snapshot_name)

        if username:
            self.audit.add_log(
                username=username,
                action='create_snapshot',
                zone_id=zone_id,
                zone_name=zone_name,
                volume_id=volume_id,
                volume_name=volume_id,
                snapshot_name=snapshot_name,
                ceph_pool=pool,
                full_snapshot_name=full_snap_name,
                dry_run=False,
                result='success' if result.success else 'failed',
                message=result.output or result.error,
                commands=command,
                client_ip=client_ip
            )

        return result.to_dict()

    def cleanup_snapshots(
        self,
        disk_id: str,
        keep_count: int,
        dry_run: bool = True,
        zone_id: Optional[str] = None,
        zone_name: Optional[str] = None,
        username: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> dict:
        """Cleanup old snapshots.

        Args:
            disk_id: The RBD volume ID
            keep_count: Number of newest snapshots to keep
            dry_run: If True, only preview without executing
            zone_id: Zone ID for audit log (optional)
            zone_name: Zone name (optional)
            username: Username for audit log (optional)
            client_ip: Client IP address (optional)

        Returns:
            Result dict with success, commands, etc.
        """
        pool = self.ceph.find_volume_pool(disk_id)

        result = self.ceph.cleanup_snapshots(disk_id, keep_count, dry_run)
        rbd_commands = ' && '.join(result.commands) if result.commands else ''

        # Build full script command for audit
        disk_file = f"/tmp/disk_ids_{disk_id}.txt"
        keep_flag = "--keep"
        dry_flag = "--dry-run" if dry_run else ""
        script_cmd = f"echo '{disk_id}' > {disk_file} && {self.ceph.snap_trim_script} {dry_flag} {keep_flag} {keep_count} {disk_file} && rm -f {disk_file}"

        if username:
            result_str = 'dryrun' if result.dry_run else ('success' if result.success else 'failed')
            # Use the detailed output from ceph_service
            message = result.output or ''
            # For audit commands field: show script command if executed, otherwise show rbd commands
            audit_commands = script_cmd if not dry_run and result.success else rbd_commands

            self.audit.add_log(
                username=username,
                action='cleanup',
                zone_id=zone_id,
                zone_name=zone_name,
                volume_id=disk_id,
                volume_name=disk_id,
                ceph_pool=pool,
                keep_count=keep_count,
                dry_run=dry_run,
                result=result_str,
                message=message,
                commands=audit_commands,
                client_ip=client_ip
            )

        return result.to_dict()

    def protect_snapshot(
        self,
        volume_id: str,
        snapshot_name: str,
        username: Optional[str] = None,
        zone_id: Optional[str] = None,
        zone_name: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> dict:
        """Protect a snapshot.

        Args:
            volume_id: The volume ID
            snapshot_name: Name of the snapshot to protect
            username: Username for audit log (optional)
            zone_id: Zone ID (optional)
            zone_name: Zone name (optional)
            client_ip: Client IP address (optional)

        Returns:
            Result dict with success, output, etc.
        """
        pool = self.ceph.find_volume_pool(volume_id)
        full_snap_name = f"{pool}/{volume_id}@{snapshot_name}" if pool else f"{volume_id}@{snapshot_name}"
        command = f"rbd snap protect {full_snap_name}"

        result = self.ceph.protect_snapshot(volume_id, snapshot_name)

        if username:
            self.audit.add_log(
                username=username,
                action='protect_snapshot',
                zone_id=zone_id,
                zone_name=zone_name,
                volume_id=volume_id,
                volume_name=volume_id,
                snapshot_name=snapshot_name,
                ceph_pool=pool,
                full_snapshot_name=full_snap_name,
                dry_run=False,
                result='success' if result.success else 'failed',
                message=result.output or result.error,
                commands=command,
                client_ip=client_ip
            )

        return result.to_dict()

    def unprotect_snapshot(
        self,
        volume_id: str,
        snapshot_name: str,
        username: Optional[str] = None,
        zone_id: Optional[str] = None,
        zone_name: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> dict:
        """Unprotect a snapshot.

        Args:
            volume_id: The volume ID
            snapshot_name: Name of the snapshot to unprotect
            username: Username for audit log (optional)
            zone_id: Zone ID (optional)
            zone_name: Zone name (optional)
            client_ip: Client IP address (optional)

        Returns:
            Result dict with success, output, etc.
        """
        pool = self.ceph.find_volume_pool(volume_id)
        full_snap_name = f"{pool}/{volume_id}@{snapshot_name}" if pool else f"{volume_id}@{snapshot_name}"
        command = f"rbd snap unprotect {full_snap_name}"

        result = self.ceph.unprotect_snapshot(volume_id, snapshot_name)

        if username:
            self.audit.add_log(
                username=username,
                action='unprotect_snapshot',
                zone_id=zone_id,
                zone_name=zone_name,
                volume_id=volume_id,
                volume_name=volume_id,
                snapshot_name=snapshot_name,
                ceph_pool=pool,
                full_snapshot_name=full_snap_name,
                dry_run=False,
                result='success' if result.success else 'failed',
                message=result.output or result.error,
                commands=command,
                client_ip=client_ip
            )

        return result.to_dict()

    def check_health(self) -> dict:
        """Check Ceph cluster health."""
        return self.ceph.check_health().to_dict()

    def list_ceph_volumes(self) -> dict:
        """List all Ceph volumes across pools."""
        try:
            pools = self.ceph.list_pools()
            all_volumes = {}
            for pool in pools:
                volumes = self.ceph.list_volumes(pool)
                for vol in volumes:
                    all_volumes[vol] = {'name': vol, 'pool': pool}
            return {'volumes': all_volumes}
        except Exception as e:
            return {'error': str(e)}
