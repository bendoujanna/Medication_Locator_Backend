import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings


def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)

class FirebaseAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return None

        id_token = auth_header.split("Bearer ")[1].strip()

        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
        except firebase_auth.ExpiredIdTokenError:
            raise AuthenticationFailed("Firebase token has expired. Please log in again.")
        except firebase_auth.InvalidIdTokenError:
            raise AuthenticationFailed("Invalid Firebase token.")
        except firebase_auth.RevokedIdTokenError:
            raise AuthenticationFailed("Firebase token has been revoked.")
        except Exception as e:
            raise AuthenticationFailed(f"Firebase authentication error: {str(e)}")

        firebase_uid = decoded_token.get("uid")
        if not firebase_uid:
            raise AuthenticationFailed("Token is missing the uid claim.")

        # Resolve the ClinicStaff profile
        try:
            from clinics.models import ClinicStaff
            staff = ClinicStaff.objects.select_related("clinic").get(
                firebase_uid=firebase_uid
            )
        except ClinicStaff.DoesNotExist:
            raise AuthenticationFailed(
                "No clinic staff account found for this Firebase user. "
                "Contact your clinic administrator."
            )

        if not staff.is_active:
            raise AuthenticationFailed(
                "This staff account has been deactivated. "
                "Contact your clinic administrator."
            )

        request.clinic_staff = staff
        return (staff, None)

    def authenticate_header(self, request):
        return "Bearer"


# Staff Provisioning Helpers

def create_firebase_user(email: str, password: str, display_name: str = "") -> str:
    user = firebase_auth.create_user(
        email=email,
        password=password,
        display_name=display_name or email,
        email_verified=False
    )
    return user.uid


def delete_firebase_user(firebase_uid: str) -> None:
    try:
        firebase_auth.delete_user(firebase_uid)
    except firebase_auth.UserNotFoundError:
        pass


def deactivate_firebase_user(firebase_uid: str) -> None:
    firebase_auth.update_user(firebase_uid, disabled=True)


def reactivate_firebase_user(firebase_uid: str) -> None:
    firebase_auth.update_user(firebase_uid, disabled=False)


def revoke_firebase_tokens(firebase_uid: str) -> None:
    firebase_auth.revoke_refresh_tokens(firebase_uid)
