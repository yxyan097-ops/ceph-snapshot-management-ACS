"""SSH 密钥管理 API"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from ceph_snapshot_manager.models.zone_key import ZoneKeyModel
from ceph_snapshot_manager.services.ssh_agent_service import SSHAgentService
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519, ec
import hashlib

admin_keys_bp = Blueprint('admin_keys', __name__)

def get_zone_key_model():
    return ZoneKeyModel()

def get_ssh_agent():
    return SSHAgentService()

@admin_keys_bp.route('/api/admin/keys', methods=['GET'])
@login_required
def list_keys():
    """获取所有 Zone 密钥列表"""
    model = get_zone_key_model()
    keys = model.get_all()
    for key in keys:
        key.pop('private_key', None)
    return jsonify({'keys': keys})

@admin_keys_bp.route('/api/admin/keys/<zone_id>', methods=['GET'])
@login_required
def get_key(zone_id):
    """获取指定 Zone 的密钥信息"""
    model = get_zone_key_model()
    key = model.get_by_zone_id(zone_id)
    if not key:
        return jsonify({'error': 'Zone 密钥不存在'}), 404
    key.pop('private_key', None)
    return jsonify(key)

def load_key_and_get_info(private_key_str):
    """Load private key and return public key and fingerprint."""
    try:
        key = serialization.load_ssh_private_key(
            private_key_str.encode(),
            password=None
        )
        pub = key.public_key()
        pub_bytes = pub.public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)

        if isinstance(key, rsa.RSAPrivateKey):
            public_key = "ssh-rsa " + pub_bytes.decode()
        elif isinstance(key, ed25519.Ed25519PrivateKey):
            public_key = "ssh-ed25519 " + pub_bytes.decode()
        elif isinstance(key, ec.EllipticCurvePrivateKey):
            public_key = "ecdsa-sha2-nistp256 " + pub_bytes.decode()
        else:
            raise ValueError("Unsupported key type: " + str(type(key)))

        # Calculate MD5 fingerprint
        der = pub.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        md5hash = hashlib.md5(der)
        fingerprint = ':'.join(a+b for a,b in zip(md5hash.hexdigest()[::2], md5hash.hexdigest()[1::2]))

        return public_key, fingerprint
    except Exception as e:
        raise ValueError("Invalid private key: " + str(e))

@admin_keys_bp.route('/api/admin/keys', methods=['POST'])
@login_required
def upload_key():
    """上传私钥并关联到 Zone"""
    data = request.get_json()
    zone_id = data.get('zone_id')
    zone_name = data.get('zone_name')
    ssh_user = data.get('ssh_user', 'root')
    private_key = data.get('private_key')

    if not all([zone_id, zone_name, private_key]):
        return jsonify({'error': '缺少必要参数'}), 400

    try:
        public_key, fingerprint = load_key_and_get_info(private_key)

        model = get_zone_key_model()
        model.add_key(
            zone_id=zone_id,
            zone_name=zone_name,
            ssh_user=ssh_user,
            private_key=private_key,
            public_key=public_key,
            fingerprint=fingerprint
        )

        agent = get_ssh_agent()
        agent.add_key(zone_id, private_key, public_key)

        return jsonify({
            'success': True,
            'public_key': public_key,
            'fingerprint': fingerprint
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@admin_keys_bp.route('/api/admin/keys/<zone_id>', methods=['PUT'])
@login_required
def update_key(zone_id):
    """更新 Zone 的密钥"""
    data = request.get_json()
    private_key = data.get('private_key')

    if not private_key:
        return jsonify({'error': '缺少私钥'}), 400

    try:
        public_key, fingerprint = load_key_and_get_info(private_key)

        model = get_zone_key_model()
        existing = model.get_by_zone_id(zone_id)
        if not existing:
            return jsonify({'error': 'Zone 密钥不存在'}), 404

        model.add_key(
            zone_id=zone_id,
            zone_name=existing['zone_name'],
            ssh_user=existing['ssh_user'],
            private_key=private_key,
            public_key=public_key,
            fingerprint=fingerprint
        )

        agent = get_ssh_agent()
        agent.remove_key(zone_id)
        agent.add_key(zone_id, private_key, public_key)

        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@admin_keys_bp.route('/api/admin/keys/<zone_id>', methods=['DELETE'])
@login_required
def delete_key(zone_id):
    """删除 Zone 的密钥"""
    model = get_zone_key_model()
    agent = get_ssh_agent()

    agent.remove_key(zone_id)
    model.delete_by_zone_id(zone_id)

    return jsonify({'success': True})