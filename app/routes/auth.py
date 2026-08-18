from flask import Blueprint, request, jsonify, session, render_template, redirect
from app.models import User
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET'])
def login_page():
    return render_template("login.html")


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

    session.clear()
    session['user_id'] = user.id
    session['role'] = user.role
    session['provider_id'] = user.provider_id

    redirect_url = "/admin" if user.role == "ADMIN" else "/provider"

    return jsonify({
        "message": "OK",
        "role": user.role,
        "redirect": redirect_url
    })


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@auth_bp.route('/me')
def me():
    if not session.get('user_id'):
        return jsonify({"authenticated": False})

    return jsonify({
        "authenticated": True,
        "role": session.get('role'),
        "provider_id": session.get('provider_id')
    })