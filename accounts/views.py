import logging
from datetime import timedelta
from ipaddress import ip_address

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import GENERIC_LOGIN_ERROR, LoginForm, ProfileForm, SignupForm
from .models import LoginAttempt, User

ACCOUNT_LOGIN_ATTEMPT_LIMIT = 5
NETWORK_LOGIN_ATTEMPT_LIMIT = 30
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_ATTEMPT_RETENTION = timedelta(minutes=30)
SIGNUP_LIMIT = 5
SIGNUP_ATTEMPT_LIMIT = 20
SIGNUP_WINDOW_SECONDS = 60 * 60
PASSWORD_CHANGE_ATTEMPT_LIMIT = 10
PASSWORD_CHANGE_WINDOW_SECONDS = 60 * 60
MAX_PASSWORD_INPUT_LENGTH = 256
security_logger = logging.getLogger("tiny_market.security")


def _account_identifier(username):
    # Bound the work performed before form validation on attacker input.
    raw_username = username if isinstance(username, str) else str(username)
    if len(raw_username) > 150:
        return "\0oversized-username"
    return User.normalize_username_value(raw_username)[:150]


def _network_identifier(request):
    # Trust X-Forwarded-For only from an explicitly configured reverse proxy
    # that replaces (rather than appends attacker-controlled) forwarding data.
    raw_address = request.META.get("REMOTE_ADDR", "")
    if raw_address in settings.TRUSTED_PROXY_IPS:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            raw_address = forwarded.split(",", 1)[0].strip()
    try:
        return ip_address(raw_address).compressed
    except ValueError:
        return "unknown"


def _key_hash(scope, identifier):
    """Return an HMAC-SHA256 digest so low-entropy identifiers stay private."""
    return salted_hmac(
        key_salt=f"accounts.login-attempt.{scope}",
        value=identifier,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def _attempt_keys(request, username):
    return (
        (
            LoginAttempt.Scope.ACCOUNT,
            _key_hash(
                LoginAttempt.Scope.ACCOUNT,
                _account_identifier(username),
            ),
        ),
        (
            LoginAttempt.Scope.NETWORK,
            _key_hash(
                LoginAttempt.Scope.NETWORK,
                _network_identifier(request),
            ),
        ),
    )


def _ordered_attempt_keys(attempt_keys):
    # Check the network first. Once it is locked, do not create arbitrary
    # account-scope rows for attacker-supplied usernames.
    return sorted(
        attempt_keys,
        key=lambda item: 0 if item[0] == LoginAttempt.Scope.NETWORK else 1,
    )


def _attempt_limit(scope):
    if scope == LoginAttempt.Scope.NETWORK:
        return NETWORK_LOGIN_ATTEMPT_LIMIT
    return ACCOUNT_LOGIN_ATTEMPT_LIMIT


def _reservation_cache_key(scope, key_hash):
    return f"tiny-market:login-reservation:{scope}:{key_hash}"


def _reserve_cache_attempts(attempt_keys):
    for scope, key_hash in _ordered_attempt_keys(attempt_keys):
        cache_key = _reservation_cache_key(scope, key_hash)
        if cache.add(cache_key, 1, timeout=int(LOGIN_WINDOW.total_seconds())):
            count = 1
        else:
            try:
                count = cache.incr(cache_key)
            except ValueError:
                count = (
                    1
                    if cache.add(
                        cache_key,
                        1,
                        timeout=int(LOGIN_WINDOW.total_seconds()),
                    )
                    else _attempt_limit(scope) + 1
                )
        if count > _attempt_limit(scope):
            return False
    return True


def _clear_cache_attempts(attempt_keys):
    cache.delete_many([_reservation_cache_key(scope, key_hash) for scope, key_hash in attempt_keys])


def _reserve_database_attempts(attempt_keys, now):
    """Reserve one password check in a short transaction, before hashing."""
    with transaction.atomic():
        for scope, key_hash in _ordered_attempt_keys(attempt_keys):
            try:
                # A savepoint keeps a concurrent unique-key race from breaking
                # the outer reservation transaction.
                with transaction.atomic():
                    LoginAttempt.objects.get_or_create(
                        scope=scope,
                        key_hash=key_hash,
                        defaults={"window_started": now},
                    )
            except IntegrityError:
                pass
            attempt = LoginAttempt.objects.select_for_update().get(
                scope=scope,
                key_hash=key_hash,
            )
            if attempt.window_started <= now - LOGIN_WINDOW:
                attempt.failures = 0
                attempt.window_started = now
                attempt.locked_until = None
            if attempt.locked_until and attempt.locked_until > now:
                return False
            attempt.failures += 1
            if attempt.failures >= _attempt_limit(scope):
                attempt.locked_until = now + LOGIN_WINDOW
            attempt.save(
                update_fields=("failures", "window_started", "locked_until"),
            )
    return True


def _clear_database_attempts(attempt_keys):
    if not attempt_keys:
        return
    query = Q()
    for scope, key_hash in attempt_keys:
        query |= Q(scope=scope, key_hash=key_hash)
    LoginAttempt.objects.filter(query).delete()


def _database_attempt_is_locked(attempt_keys, now):
    for scope, key_hash in _ordered_attempt_keys(attempt_keys):
        if LoginAttempt.objects.filter(
            scope=scope,
            key_hash=key_hash,
            locked_until__gt=now,
        ).exists():
            return True
    return False


def _purge_expired_login_attempts(now):
    cleanup_key = "tiny-market:login-attempt-cleanup"
    if not cache.add(
        cleanup_key,
        1,
        timeout=int(LOGIN_WINDOW.total_seconds()),
    ):
        return
    cutoff = now - LOGIN_ATTEMPT_RETENTION
    LoginAttempt.objects.filter(window_started__lte=cutoff).filter(
        Q(locked_until__isnull=True) | Q(locked_until__lte=now)
    ).delete()


def _reserve_authentication_attempt(attempt_keys, now):
    # The cache gives an atomic fast gate in the configured process/shared
    # cache. The DB preserves the lock window across process restarts. Neither
    # lock is held while an expensive password hash is evaluated.
    _purge_expired_login_attempts(now)
    if _database_attempt_is_locked(attempt_keys, now):
        return False
    if not _reserve_cache_attempts(attempt_keys):
        return False
    return _reserve_database_attempts(attempt_keys, now)


def _clear_successful_account_attempts(attempt_keys):
    account_keys = tuple(
        (scope, key_hash) for scope, key_hash in attempt_keys if scope == LoginAttempt.Scope.ACCOUNT
    )
    _clear_cache_attempts(account_keys)
    _clear_database_attempts(account_keys)


def _generic_login_form(request, username):
    display_username = username if isinstance(username, str) and len(username) <= 150 else ""
    form = LoginForm(
        request=request,
        data={"username": display_username, "password": str()},
    )
    # Validate only an empty password, then replace the required-field error
    # with one generic response. This initializes Django's error container
    # without invoking password hashing a second time.
    form.is_valid()
    form.errors.clear()
    form.add_error(None, GENERIC_LOGIN_ERROR)
    return form


def _safe_next_url(request):
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return None


def _consume_network_limit(request, action, limit, timeout):
    """Atomically count an action without retaining a raw network address."""
    key = _key_hash(action, _network_identifier(request))
    cache_key = f"tiny-market:{action}:{key}"
    if cache.add(cache_key, 1, timeout=timeout):
        return True
    try:
        return cache.incr(cache_key) <= limit
    except ValueError:
        # A concurrent expiry can remove the key between add() and incr().
        return cache.add(cache_key, 1, timeout=timeout)


def _consume_user_limit(user_id, action, limit, timeout):
    """Atomically rate-limit an authenticated action without a raw user ID key."""
    key = _key_hash(action, str(user_id))
    cache_key = f"tiny-market:{action}:{key}"
    if cache.add(cache_key, 1, timeout=timeout):
        return True
    try:
        return cache.incr(cache_key) <= limit
    except ValueError:
        return cache.add(cache_key, 1, timeout=timeout)


@sensitive_post_parameters("password1", "password2")
@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("market:home")

    if request.method == "POST" and not _consume_network_limit(
        request,
        "signup-attempt",
        SIGNUP_ATTEMPT_LIMIT,
        SIGNUP_WINDOW_SECONDS,
    ):
        security_logger.warning("signup_attempt_rate_limited")
        return HttpResponse(
            "회원가입 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
            status=429,
            content_type="text/plain; charset=utf-8",
        )
    if request.method == "POST" and (
        len(request.POST.get("username", "")) > 150
        or len(request.POST.get("password1", "")) > MAX_PASSWORD_INPUT_LENGTH
        or len(request.POST.get("password2", "")) > MAX_PASSWORD_INPUT_LENGTH
    ):
        return HttpResponse(
            "입력값을 확인해 주세요.",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not _consume_network_limit(
            request,
            "signup-success",
            SIGNUP_LIMIT,
            SIGNUP_WINDOW_SECONDS,
        ):
            security_logger.warning("signup_rate_limited")
            form.add_error(None, "회원가입 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
            return render(
                request,
                "registration/signup.html",
                {"form": form},
                status=429,
            )
        with transaction.atomic():
            user = form.save()

            # Runtime import avoids coupling app startup to market service setup.
            from market import services

            services.ensure_wallet(user)
            services.issue_demo_points(user, 100_000)

        security_logger.info("signup_succeeded actor=%s", user.pk)
        messages.success(request, "회원가입이 완료되었습니다. 로그인해 주세요.")
        return redirect("accounts:login")

    return render(request, "registration/signup.html", {"form": form})


@sensitive_post_parameters("password")
@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("market:home")

    next_url = _safe_next_url(request)
    form = LoginForm(request=request, data=request.POST or None)

    if request.method == "POST":
        username = request.POST.get("username", "")
        credentials_oversized = (
            len(username) > 150 or len(request.POST.get("password", "")) > MAX_PASSWORD_INPUT_LENGTH
        )
        attempt_keys = _attempt_keys(request, username)
        now = timezone.now()

        authenticated_user = None
        is_locked = not _reserve_authentication_attempt(attempt_keys, now)
        if not is_locked and not credentials_oversized and form.is_valid():
            authenticated_user = form.get_user()
            _clear_successful_account_attempts(attempt_keys)

        if is_locked:
            security_logger.warning(
                "login_rate_limited account_key=%s network_key=%s",
                attempt_keys[0][1][:12],
                attempt_keys[1][1][:12],
            )
            form = _generic_login_form(request, username)
        elif authenticated_user is not None:
            auth_login(request, authenticated_user)
            security_logger.info("login_succeeded actor=%s", request.user.pk)
            return redirect(next_url or "market:home")
        else:
            security_logger.warning(
                "login_failed account_key=%s network_key=%s",
                attempt_keys[0][1][:12],
                attempt_keys[1][1][:12],
            )
            form = _generic_login_form(request, username)

    return render(
        request,
        "registration/login.html",
        {"form": form, "next": next_url or ""},
    )


@sensitive_post_parameters("password")
@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_login_view(request):
    """Apply the same account/network throttling before Django admin auth."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("admin:index")
        return HttpResponse(
            "관리자 로그인 전에 현재 사용자 세션을 종료해 주세요.",
            status=403,
            content_type="text/plain; charset=utf-8",
        )
    if request.method == "GET":
        return admin.site.login(request)

    username = request.POST.get("username", "")
    credentials_oversized = (
        len(username) > 150 or len(request.POST.get("password", "")) > MAX_PASSWORD_INPUT_LENGTH
    )
    attempt_keys = _attempt_keys(request, username)
    now = timezone.now()
    response = None
    is_locked = not _reserve_authentication_attempt(attempt_keys, now)
    if not is_locked and not credentials_oversized:
        response = admin.site.login(request)
        submitted_username = _account_identifier(username)
        authenticated = (
            response.status_code in {301, 302, 303, 307, 308}
            and request.user.is_authenticated
            and request.user.is_staff
            and request.user.username == submitted_username
        )
        if authenticated:
            _clear_successful_account_attempts(attempt_keys)
    elif not is_locked:
        authenticated = False
        response = HttpResponse(
            "로그인 정보를 확인해 주세요.",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    if is_locked:
        security_logger.warning("admin_login_rate_limited")
        return HttpResponse(
            "로그인 정보를 확인하거나 잠시 후 다시 시도해 주세요.",
            status=429,
            content_type="text/plain; charset=utf-8",
        )

    if authenticated:
        security_logger.info("admin_login_succeeded actor=%s", request.user.pk)
    else:
        security_logger.warning(
            "admin_login_failed account_key=%s network_key=%s",
            attempt_keys[0][1][:12],
            attempt_keys[1][1][:12],
        )
    return response


@sensitive_post_parameters()
@never_cache
@csrf_protect
@require_POST
def logout_view(request):
    actor_id = request.user.pk if request.user.is_authenticated else None
    auth_logout(request)
    security_logger.info("logout actor=%s", actor_id)
    messages.info(request, "로그아웃되었습니다.")
    return redirect("market:home")


def _inactive_session_response(request):
    """End a stale session if an account became unusable after login."""
    if request.user.is_active and not request.user.is_suspended:
        return None
    actor_id = request.user.pk
    auth_logout(request)
    security_logger.warning("inactive_account_session_rejected actor=%s", actor_id)
    return redirect("accounts:login")


def _render_mypage(request, *, profile_form, password_form, status=200):
    return render(
        request,
        "accounts/mypage.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
        },
        status=status,
    )


@never_cache
@require_GET
def public_profile_view(request, username):
    """Show the allowlisted public fields of an active ordinary account."""
    normalized_username = User.normalize_username_value(username)
    profile_user = get_object_or_404(
        User.objects.filter(
            is_active=True,
            is_suspended=False,
            is_staff=False,
            is_superuser=False,
        ).only("username", "bio"),
        username=normalized_username,
    )
    # Pass primitives rather than the User object so future template changes
    # cannot accidentally disclose email, privilege, or suspension metadata.
    profile = {
        "username": profile_user.username,
        "bio": profile_user.bio,
    }
    return render(request, "accounts/public_profile.html", {"profile": profile})


@login_required
@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def mypage_view(request):
    stale_session_response = _inactive_session_response(request)
    if stale_session_response is not None:
        return stale_session_response

    profile_form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and profile_form.is_valid():
        # Save only the allowlisted field to avoid stale or forged account-state
        # values being persisted with the profile update.
        request.user.bio = profile_form.cleaned_data["bio"]
        request.user.save(update_fields=("bio",))
        security_logger.info("profile_updated actor=%s", request.user.pk)
        messages.success(request, "소개글을 변경했습니다.")
        return redirect("accounts:mypage")

    return _render_mypage(
        request,
        profile_form=profile_form,
        password_form=PasswordChangeForm(user=request.user),
        status=400 if request.method == "POST" else 200,
    )


@sensitive_post_parameters("old_password", "new_password1", "new_password2")
@login_required
@never_cache
@csrf_protect
@require_POST
def password_change_view(request):
    stale_session_response = _inactive_session_response(request)
    if stale_session_response is not None:
        return stale_session_response

    if not _consume_user_limit(
        request.user.pk,
        "password-change-attempt",
        PASSWORD_CHANGE_ATTEMPT_LIMIT,
        PASSWORD_CHANGE_WINDOW_SECONDS,
    ):
        security_logger.warning("password_change_rate_limited actor=%s", request.user.pk)
        response = HttpResponse(
            "비밀번호 변경 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
            status=429,
            content_type="text/plain; charset=utf-8",
        )
        response.headers["Retry-After"] = str(PASSWORD_CHANGE_WINDOW_SECONDS)
        return response

    password_fields = ("old_password", "new_password1", "new_password2")
    if any(
        len(request.POST.get(field_name, "")) > MAX_PASSWORD_INPUT_LENGTH
        for field_name in password_fields
    ):
        security_logger.warning("password_change_input_rejected actor=%s", request.user.pk)
        return HttpResponse(
            "비밀번호 입력값을 확인해 주세요.",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    password_form = PasswordChangeForm(user=request.user, data=request.POST)
    if password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)
        security_logger.info("password_changed actor=%s", user.pk)
        messages.success(request, "비밀번호를 안전하게 변경했습니다.")
        return redirect("accounts:mypage")

    return _render_mypage(
        request,
        profile_form=ProfileForm(instance=request.user),
        password_form=password_form,
        status=400,
    )
