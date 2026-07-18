from django.urls import path
from accounts.views import(
    RegisterAPIView, 
    LoginAPIView, 
    VerifyEmailAPIView, 
    ResendVerificationEmailAPIView, 
    RefreshTokenAPIView, 
    LogoutAPIView, 
    PasswordResetRequestAPIView,
    PasswordResetConfirmAPIView,
    GoogleLoginAPIView
)



urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('verify-email/', VerifyEmailAPIView.as_view(), name='verify-email'),
    path('resend-verification/', ResendVerificationEmailAPIView.as_view(), name='resend-verification'),
    path('refresh/', RefreshTokenAPIView.as_view(), name='refresh'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('password-reset/', PasswordResetRequestAPIView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmAPIView.as_view(), name='password-reset-confirm'),
    path('google-login/', GoogleLoginAPIView.as_view(), name='google-login'),
]
