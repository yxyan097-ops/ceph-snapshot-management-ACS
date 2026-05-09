"""JSON response helpers."""
from flask import jsonify


def success_response(data=None, **kwargs):
    """Create a success JSON response."""
    response = {'success': True}
    if data is not None:
        response.update(data)
    response.update(kwargs)
    return jsonify(response)


def error_response(error, status_code=400):
    """Create an error JSON response."""
    return jsonify({'error': error}), status_code
