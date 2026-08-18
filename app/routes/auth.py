from flask import Blueprint, request, jsonify, session, render_template, redirect
from app.models import User
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)


# ======================================================
# 🖥️ LOGIN PAGE
# ======================================================
@auth_bp.route('/login', methods=['GET'])
def login_page():
    return render_template("login.html")


# ======================================================
# 🔐 LOGIN
# ======================================================
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data"}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"error": "Попълни всички полета"}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # ✅ SESSION
    session.clear()  # 🔥 важно
    session['user_id'] = user.id
    session['role'] = user.role
    session['barber_id'] = user.barber_id

    # 🔥 redirect логика
    redirect_url = "/admin" if user.role == "ADMIN" else "/barber"

    return jsonify({
        "message": "OK",
        "role": user.role,
        "redirect": redirect_url
    })


# ======================================================
# 🚪 LOGOUT
# ======================================================
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ======================================================
# 🔍 CHECK SESSION (много полезно)
# ======================================================
@auth_bp.route('/me')
def me():
    if not session.get('user_id'):
        return jsonify({"authenticated": False})

    return jsonify({
        "authenticated": True,
        "role": session.get('role'),
        "barber_id": session.get('barber_id')
    })