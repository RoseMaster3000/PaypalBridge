from flask import request, jsonify
from PaypalWebsite.cashout_validator import validate_cashout
from PaypalWebsite.decorators import none_required
import traceback

def register_preview_cashout_route(app):
    @app.route('/PreviewCashout', methods=['POST'])
    @none_required
    def PreviewCashoutPost(user):
        try:
            # 1) Must have a user
            if not user:
                return jsonify({
                    "success": False,
                    "message": "User not found. Please restart the game or log in again.",   
                }), 200

            # 2) Parse gems safely
            raw_gems = request.form.get("gems", "").strip()
            if not raw_gems:
                return jsonify({
                    "success": False,
                    "message": "Missing gem amount.",
                }), 200

            try:
                gemCount = int(raw_gems)
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": "Invalid gem amount.",
                }), 200

            # 3) Delegate to validator
            data = validate_cashout(user, gemCount)
            return jsonify(data), 200

        except Exception as e:
            print("PREVIEW ERROR:", e)
            traceback.print_exc()
            return jsonify({
                "success": False,
                "message": "Server error"
            }), 500