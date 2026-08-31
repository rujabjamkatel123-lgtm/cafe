from flask import Blueprint

from app.controllers.auth import AuthController
from app.auth import login_required, role_required


class AuthRoutes:

    def __init__(self):
        self.bp = Blueprint("auth", __name__)
        self.controller = AuthController()

    def register(self):

        # =====================================================
        # AUTHENTICATION ROUTES
        # =====================================================

        # ── Login ────────────────────────────────────────────
        self.bp.route(
            "/login",
            methods=["GET", "POST"]
        )(
            self.controller.login
        )

        # ── Mobile Login ─────────────────────────────────────
        self.bp.route(
            "/mobile-login",
            methods=["GET", "POST"]
        )(
            self.controller.mobile_login
        )

        # ── Register Customer ────────────────────────────────
        self.bp.route(
            "/register",
            methods=["GET", "POST"]
        )(
            self.controller.register
        )

        # ── Forgot Password ──────────────────────────────────
        self.bp.route(
            "/forgot-password",
            methods=["GET", "POST"]
        )(
            self.controller.forgot_password
        )

        # ── Verify OTP ───────────────────────────────────────
        self.bp.route(
            "/verify-otp",
            methods=["GET", "POST"]
        )(
            self.controller.verify_otp
        )

        # ── Logout ───────────────────────────────────────────
        self.bp.route(
            "/logout",
            methods=["GET", "POST"]
        )(
            self.controller.logout
        )


        # =====================================================
        # CUSTOMER ROUTES
        # =====================================================


        # =====================================================
        # RECEPTIONIST ROUTES
        # =====================================================


        # =====================================================
        # RETURN BLUEPRINT
        # =====================================================

        return self.bp