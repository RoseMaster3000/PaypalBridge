from flask import request, jsonify
from PaypalWebsite.cashout_validator import validate_cashout
from PaypalWebsite.decorators import none_required
import traceback

print("Loaded routes_preview_cashout.py")

def register_preview_cashout_route(app):
    print("Registering /PreviewCashout route")
    @app.route('/PreviewCashout', methods=['POST'])
    @none_required
    def PreviewCashoutPost(user):
        try:
            gemCount = int(request.form["gems"])
            data = validate_cashout(user, gemCount)
            return jsonify(data)

        except Exception as e:
            print("PREVIEW ERROR:", e)
            traceback.print_exc()
            return jsonify({
                "success": False,
                "message": "Server error"
            }), 500