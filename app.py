"""Flask application entry point - delegates to ceph_snapshot_manager package."""
import configparser

# Import the application factory
from ceph_snapshot_manager import create_app


def main():
    """Run the Flask application."""
    config_path = 'config.ini'
    app = create_app(config_path)

    # Load additional config for host/port
    config = configparser.ConfigParser()
    config.read(config_path)

    host = config.get('app', 'host', fallback='0.0.0.0')
    port = config.getint('app', 'port', fallback=5000)
    debug = config.getboolean('app', 'debug', fallback=False)

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
