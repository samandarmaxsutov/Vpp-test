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

app = Flask(__name__)
CORS(app)

# Register all blueprints
app.register_blueprint(interfaces_bp)
app.register_blueprint(routes_bp)
app.register_blueprint(acls_bp)
app.register_blueprint(nat_bp)
app.register_blueprint(stats_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(dhcp_bp)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
 
    