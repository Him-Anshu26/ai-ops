from rest_framework import serializers
from accounts.models import User

from django.contrib.auth.password_validation import (
    validate_password,
)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name']


    def validate_email(self, value):

        value = value.lower().strip()

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_password(self, value):

        validate_password(value)

        return value
    
    def validate_first_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError("First name is required.")
        return value
    

    

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


    def validate_email(self, value):

        value = value.lower().strip()
        return value
    
    



class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()   

    def validate_email(self, value):

        value = value.lower().strip()
        return value
    



class PasswordResetConfirmSerializer(serializers.Serializer):

    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_token(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Token is required."
            )

        return value

    def validate_new_password(self, value):

        validate_password(value)

        return value
    



class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True) 

    def validate_refresh(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Refresh token is required."
            )

        return value  
    

class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)

    def validate_id_token(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Google ID token is required."
            )

        return value