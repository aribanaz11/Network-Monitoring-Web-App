import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import User, UserRole

@pytest.mark.django_db
class TestAuthentication:
    def test_user_registration(self, client):
        url = reverse('auth_register')
        data = {
            'email': 'newdev@netwatch.io',
            'full_name': 'New Engineer',
            'password': 'StrongPassword@2026',
            'password_confirm': 'StrongPassword@2026',
            'role': UserRole.OPERATOR
        }
        response = client.post(url, data, content_type='application/json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'newdev@netwatch.io'
        assert response.data['role'] == UserRole.OPERATOR
        assert User.objects.filter(email='newdev@netwatch.io').exists()

    def test_login_and_jwt_claims(self, client):
        user = User.objects.create_user(
            email='ops@netwatch.io',
            password='Password123!',
            full_name='Ops Lead',
            role=UserRole.OPERATOR
        )
        url = reverse('token_obtain_pair')
        response = client.post(url, {'email': 'ops@netwatch.io', 'password': 'Password123!'}, content_type='application/json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['user']['email'] == 'ops@netwatch.io'
        assert response.data['user']['role'] == UserRole.OPERATOR

    def test_rbac_admin_vs_viewer_permissions(self, client):
        admin = User.objects.create_superuser(email='super@netwatch.io', password='AdminPass123!')
        viewer = User.objects.create_user(email='view@netwatch.io', password='ViewerPass123!', role=UserRole.VIEWER)

        # Login as viewer
        login_resp = client.post(reverse('token_obtain_pair'), {'email': 'view@netwatch.io', 'password': 'ViewerPass123!'}, content_type='application/json')
        viewer_token = login_resp.data['access']

        # Viewer attempting to list users (Admin only)
        resp = client.get(reverse('user_list'), HTTP_AUTHORIZATION=f'Bearer {viewer_token}')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        # Login as admin
        admin_login = client.post(reverse('token_obtain_pair'), {'email': 'super@netwatch.io', 'password': 'AdminPass123!'}, content_type='application/json')
        admin_token = admin_login.data['access']

        # Admin listing users
        resp_admin = client.get(reverse('user_list'), HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        assert resp_admin.status_code == status.HTTP_200_OK
