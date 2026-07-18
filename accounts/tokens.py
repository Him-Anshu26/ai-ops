from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError

from accounts.models import User


def generate_access_token(user: User, session_id: str) -> str:
    """
    Generate short-lived access token.
    """

    # create base refresh token for the user (this will not be used as refresh token but we can use it to create access token)
    refresh = RefreshToken.for_user(user)
    
    # Extract access token from refresh token
    #
    # Access token lifetime:
    # usually 15 minutes
    access_token = refresh.access_token

     

    # Add custom JWT payload claims
    #
    # user_id:
    # identifies authenticated user
    #
    # session_id:
    # connects JWT to DB session    
    access_token["user_id"] = user.id
    access_token["session_id"] = session_id


    # Convert token object → string JWT
    #
    # Example:
    # eyJhbGciOiJIUzI1NiIs...
    return str(access_token)


def generate_refresh_token(user: User, session_id: str) -> str:
    """
    Generate long-lived refresh token.
    """

    # Create refresh token object
    #
    # Refresh token lifetime:
    # usually 7 days
    refresh = RefreshToken.for_user(user)

    # Add custom payload claims
    #
    # Important:
    # refresh token also carries session_id
    #
    # Used during:
    # refresh token validation
    refresh["user_id"] = user.id
    refresh["session_id"] = session_id

    # Convert token object → string JWT
    return str(refresh)


def decode_token(token: str) -> dict | None:
    """
    Decode and validate JWT token.
    Returns payload if valid else None if Invalid or Expired.
    """

    try:
        # Try decoding as access token
        #
        # Automatically validates:
        # - expiry
        # - signature
        # - token format
        payload = AccessToken(token)


        # Return decoded JWT payload dictionary
        #
        # Example:
        # {
        #     "user_id": 1,
        #     "session_id": "...",
        #     "exp": ...
        # }
        return payload.payload

    except TokenError:
        try:
            # If access token decoding fails,
            # try decoding as refresh token
            payload = RefreshToken(token)
            
            # Return decoded refresh payload
            return payload.payload

        except TokenError:

            # Invalid token
            # Expired token
            # Tampered token
            # Wrong signature
            return None