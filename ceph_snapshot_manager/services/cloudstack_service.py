"""CloudStack API service."""
import os
from urllib.parse import urlparse
from typing import List, Optional

os.environ['LIBCLOUD_IGNORE_SSL_ERRORS'] = '1'

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

from ceph_snapshot_manager.config.settings import CloudStackConfig


class CloudStackService:
    """CloudStack API operations."""

    def __init__(self, config: CloudStackConfig):
        self.url = config.url
        self.api_key = config.api_key
        self.secret_key = config.secret_key
        self._driver = self._get_driver()

    def _get_driver(self):
        """Get or create the libcloud driver instance."""
        cls = get_driver(Provider.CLOUDSTACK)
        parsed = urlparse(self.url)
        host = parsed.hostname
        port = parsed.port or 8080
        path = parsed.path or '/client/api'
        return cls(
            key=self.api_key,
            secret=self.secret_key,
            host=host,
            path=path,
            port=port,
            secure=False
        )

    def _get_instance_name(self, instance_id: str, nodes_cache: dict) -> str:
        """Get instance name from cache."""
        return nodes_cache.get(instance_id, '')

    def list_zones(self) -> List[dict]:
        """List all available zones."""
        locations = self._driver.list_locations()
        return [{'id': loc.id, 'name': loc.name} for loc in locations]

    def list_volumes(self, zone_id: Optional[str] = None) -> List[dict]:
        """List volumes, optionally filtered by zone."""
        volumes = self._driver.list_volumes()
        nodes_cache = {node.id: node.name for node in self._driver.list_nodes()}

        result = []
        for vol in volumes:
            instance_id = vol.extra.get('instance_id', '')
            vol_dict = {
                'id': vol.id,
                'name': vol.name,
                'size': getattr(vol, 'size', 0) or 0,
                'state': getattr(vol, 'state', 'unknown') or 'unknown',
                'type': vol.extra.get('volume_type', 'DATADISK'),
                'zone_id': vol.extra.get('zone_id'),
                'instance_id': instance_id,
                'instance_name': self._get_instance_name(instance_id, nodes_cache) if instance_id else ''
            }
            result.append(vol_dict)
        return result

    def list_snapshots(self, volume_id: Optional[str] = None, zone_id: Optional[str] = None) -> List[dict]:
        """List snapshots, optionally filtered by volume."""
        try:
            snapshots = self._driver.list_snapshots()
        except Exception:
            return []

        if volume_id:
            snapshots = [s for s in snapshots if s.extra.get('volume_id') == volume_id]

        return [
            {
                'id': s.id,
                'name': s.name,
                'volume_id': s.extra.get('volume_id'),
                'state': s.state,
                'created': s.extra.get('created', '')
            }
            for s in snapshots
        ]

    def get_volume_snapshot_count(self, volume_id: str) -> int:
        """Get count of snapshots for a volume."""
        try:
            snapshots = self._driver.list_snapshots()
            return len([s for s in snapshots if s.extra.get('volume_id') == volume_id])
        except Exception:
            return 0
