from flask import Flask, render_template
from flask_cors import CORS

# Import blueprints
from api.interfaces import interfaces_bp
from api.routes import routes_bp
from api.acls import acls_bp
from api.nat import nat_bp
from api.stats import stats_bp
from api.dashboard import dashboard_bp
from api.dhcp import dhcp_bp
from api.policer import policers_bp

# Import VPP teardown initializer
from vpp_connection import init_vpp_teardown


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register all blueprints (no route changes!)
    app.register_blueprint(interfaces_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(acls_bp)
    app.register_blueprint(nat_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(dhcp_bp)
    app.register_blueprint(policers_bp)

    # Register per-request VPP teardown cleanup
    init_vpp_teardown(app)

    # Frontend route untouched
    @app.route('/')
    def index():
        return render_template('index.html')

    return app


app = create_app()

if __name__ == '__main__':
    # ❗ Debug mode DISABLED — prevents reloader from breaking VPP socket
    app.run(host='0.0.0.0', port=5000, debug=True)
