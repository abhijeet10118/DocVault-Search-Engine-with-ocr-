from rest_framework import serializers
from .models import User, BRANCH_CHOICES


VALID_BRANCHES = [b[0] for b in BRANCH_CHOICES]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'password', 'branch']

    def validate_branch(self, value):
        if value not in VALID_BRANCHES:
            raise serializers.ValidationError(
                f"Invalid branch. Choose from: {', '.join(VALID_BRANCHES)}"
            )
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            branch=validated_data['branch'],
        )
        return user