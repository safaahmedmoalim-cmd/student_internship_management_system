from django.db.models import Count
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Role, User
from .serializers import (
    ChangePasswordSerializer, LoginSerializer, ProfileUpdateSerializer,
    RegisterSerializer, SupervisorBriefSerializer, UserSerializer,
)


def auth_payload(user, token):
    return {'token': token.key, 'user': UserSerializer(user).data}


class RegisterView(APIView):
    """POST /api/auth/register/  - create an account and sign in."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(auth_payload(user, token), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/auth/login/  {email, password, role?}"""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response(auth_payload(user, token))


class LogoutView(APIView):
    """POST /api/auth/logout/  - invalidates the caller's token."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET /api/auth/me/  and  PATCH /api/auth/me/  (edit own profile)."""

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/  - returns a fresh token (the old one stops working)."""

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)
        return Response({'token': token.key})


class SupervisorListView(generics.ListAPIView):
    """GET /api/supervisors/?role=academic|industrial

    Students use the industrial list when submitting a placement; the
    coordinator uses both lists when assigning supervisors.
    """
    serializer_class = SupervisorBriefSerializer

    def get_queryset(self):
        role = self.request.query_params.get('role')
        qs = User.objects.filter(is_active=True, role__in=[Role.ACADEMIC, Role.INDUSTRIAL])
        if role in (Role.ACADEMIC, Role.INDUSTRIAL):
            qs = qs.filter(role=role)
        if self.request.user.role != Role.COORDINATOR:
            qs = qs.filter(role=Role.INDUSTRIAL)  # others only need to pick an industrial supervisor
        return qs.order_by('name')
