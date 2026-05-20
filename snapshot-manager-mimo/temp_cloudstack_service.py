"""CloudStack API service - direct API calls without libcloud."""
import re
import hashlib
import hmac
import base64
import urllib.parse
from collections import OrderedDict
from typing import List, Optional, Tuple

import requests

from ceph_snapshot_manager.config.settings import CloudStackConfig


class CloudStackService:
    """CloudStack API operations using direct HTTP calls."""

    def __init__(self, config: CloudStackConfig):
        self.url = config.url
        self.api_key = config.api_key
        self.secret_key = config.secret_key

    def _sign(self, params: OrderedDict) -> str:
        """Generate CloudStack API signature."""
        # Sort parameters by key
        sorted_params = sorted(params.items())
        # Encode parameters
        encoded = '&'.join([
            '='.join([k, urllib.parse.quote_plus(str(v))])
            for k, v in sorted_params
        ])
        # Create signature using HMAC-SHA1
        signature = hmac.new(
            self.secret_key.encode(),
            encoded.lower().encode(),
            hashlib.sha1
        ).digest()
        return base64.b64encode(signature).decode()

    def _api_call(self, command: str, **kwargs) -> dict:
        """Make a CloudStack API call."""
        params = OrderedDict([('command', command), ('response', 'json')])
        params.update(kwargs)
        params['apiKey'] = self.api_key

        signature = self._sign(params)
        params['signature'] = signature

        url = self.url + '?' + '&'.join([
            '='.join([k, urllib.parse.quote_plus(str(v))])
            for k, v in params.items()
        ])

        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def list_zones(self) -> List[dict]:
        """List all available zones."""
        try:
            result = self._api_call('listZones')
            zones = result.get('listzonesresponse', {}).get('zone', [])
            if isinstance(zones, dict):
                zones = [zones]
            return [{'id': z['id'], 'name': z['name']} for z in zones]
        except Exception as e:
            print(f"Error listing zones: {e}")
            return []

    @staticmethod
    def _categorize_os(template_name: str, os_type_name: str = '') -> Tuple[str, str]:
        """Categorize VM OS into Windows/Linux and extract detailed version.

        Returns:
            (os_category, os_version): e.g. ('Linux', 'CentOS 7.6') or ('Windows', 'Windows Server 2019')
        """
        name = (template_name or '').strip()
        os_type = (os_type_name or '').strip()
        combined = f"{name} {os_type}".lower()

        # Windows detection
        if any(kw in combined for kw in ['windows', 'win server', 'win20', 'win10', 'win11', 'win7', 'win8']):
            # Try to extract specific version
            for pattern in ['Windows Server 2025', 'Windows Server 2022', 'Windows Server 2019',
                            'Windows Server 2016', 'Windows Server 2012', 'Windows 11', 'Windows 10',
                            'Windows 7', 'Windows Server']:
                if pattern.lower() in combined:
                    return 'Windows', pattern
            return 'Windows', name if name else os_type or 'Windows'

        # Linux distribution detection
        linux_distros = [
            ('centos', 'CentOS'), ('ubuntu', 'Ubuntu'), ('debian', 'Debian'),
            ('rhel', 'RHEL'), ('red hat', 'RHEL'), ('suse', 'SUSE'), ('opensuse', 'openSUSE'),
            ('fedora', 'Fedora'), ('rocky', 'Rocky Linux'), ('alma', 'AlmaLinux'),
            ('oracle', 'Oracle Linux'), ('almalinux', 'AlmaLinux'), ('rockylinux', 'Rocky Linux'),
            ('alinux', 'Alibaba Cloud Linux'), ('anolis', 'Anolis OS'), ('kylin', 'Kylin OS'),
            ('uos', 'UOS'), ('deepin', 'Deepin'), ('gentoo', 'Gentoo'), ('arch', 'Arch Linux'),
            ('amazon', 'Amazon Linux'), ('coreos', 'CoreOS'), ('flatcar', 'Flatcar'),
        ]
        for keyword, distro_name in linux_distros:
            if keyword in combined:
                # Try to extract version number
                version_match = re.search(rf'{keyword}\s*[\s-]*(\d[\d.]*)', combined, re.IGNORECASE)
                if version_match:
                    return 'Linux', f"{distro_name} {version_match.group(1)}"
                return 'Linux', distro_name

        # If template name exists but not matched, check if it looks like a Linux distro
        if name:
            # If there's a template name and it's not clearly Windows, assume Linux
            if not any(kw in combined for kw in ['windows', 'vmware', 'hyperv', 'xen']):
                return 'Linux', name

        return '未知', name if name else '未知'

    def list_volumes(self, zone_id: Optional[str] = None) -> List[dict]:
        """List volumes, optionally filtered by zone."""
        try:
            result = self._api_call('listVolumes', zoneid=zone_id)
            volumes = result.get('listvolumesresponse', {}).get('volume', [])
            if isinstance(volumes, dict):
                volumes = [volumes]

            # Get instance info for association (name + OS type)
            instances = {}
            try:
                inst_result = self._api_call('listVirtualMachines')
                vms = inst_result.get('listvirtualmachinesresponse', {}).get('virtualmachine', [])
                if isinstance(vms, dict):
                    vms = [vms]
                for vm in vms:
                    template_name = vm.get('templatename', '') or vm.get('ostypename', '')
                    os_type_name = vm.get('ostypename', '')
                    os_category, os_version = self._categorize_os(template_name, os_type_name)
                    instances[vm['id']] = {
                        'name': vm.get('name', ''),
                        'os_category': os_category,
                        'os_version': os_version,
                    }
            except Exception as e:
                print(f"Warning: Failed to fetch VM info: {e}")

            return [
                {
                    'id': v['id'],
                    'name': v.get('name', v['id']),
                    'size': int(v.get('size', 0)),
                    'state': v.get('state', 'unknown'),
                    'type': v.get('type', 'DATADISK'),
                    'zone_id': v.get('zoneid'),
                    'instance_id': v.get('instanceid', ''),
                    'instance_name': instances.get(v.get('instanceid', ''), {}).get('name', ''),
                    'os_category': instances.get(v.get('instanceid', ''), {}).get('os_category', '未知'),
                    'os_version': instances.get(v.get('instanceid', ''), {}).get('os_version', '未知'),
                }
                for v in volumes
            ]
        except Exception as e:
            print(f"Error listing volumes: {e}")
            return []

    def list_snapshots(self, volume_id: Optional[str] = None, zone_id: Optional[str] = None) -> List[dict]:
        """List snapshots, optionally filtered by volume."""
        try:
            result = self._api_call('listSnapshots', volumeid=volume_id, zoneid=zone_id)
            snapshots = result.get('listsnapshotsresponse', {}).get('snapshot', [])
            if isinstance(snapshots, dict):
                snapshots = [snapshots]
            return [
                {
                    'id': s['id'],
                    'name': s.get('name', s['id']),
                    'volume_id': s.get('volumeid'),
                    'state': s.get('state', ''),
                    'created': s.get('created', '')
                }
                for s in snapshots
            ]
        except Exception as e:
            print(f"Error listing snapshots: {e}")
            return []

    def get_volume_snapshot_count(self, volume_id: str) -> int:
        """Get count of snapshots for a volume."""
        try:
            result = self._api_call('listSnapshots', volumeid=volume_id)
            snapshots = result.get('listsnapshotsresponse', {}).get('snapshot', [])
            if isinstance(snapshots, dict):
                return 1
            return len(snapshots)
        except:
            return 0
