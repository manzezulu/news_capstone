"""DRF serializers."""

from rest_framework import serializers

from .models import Article, CustomUser, Newsletter, Publisher
from .selectors import approved_articles


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ('id', 'name', 'description', 'editors', 'journalists')
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'id',
            'username',
            'email',
            'role',
            'subscribed_publishers',
            'subscribed_journalists',
        )
        read_only_fields = fields


class ArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source='author.username', read_only=True
    )
    publisher_name = serializers.CharField(
        source='publisher.name', read_only=True, allow_null=True
    )

    class Meta:
        model = Article
        fields = (
            'id',
            'title',
            'content',
            'author',
            'author_name',
            'publisher',
            'publisher_name',
            'created_at',
            'approved',
        )
        read_only_fields = ('author', 'created_at')

    def validate_approved(self, value):
        """Only editors may change the approval state."""
        user = self.context['request'].user
        current = self.instance.approved if self.instance else False
        if value != current and user.role != CustomUser.Role.EDITOR:
            raise serializers.ValidationError(
                'Only editors can approve articles.'
            )
        return value

    def validate_publisher(self, publisher):
        """A journalist may only publish under their own publishers."""
        user = self.context['request'].user
        if (
            publisher
            and user.role == CustomUser.Role.JOURNALIST
            and not publisher.journalists.filter(pk=user.pk).exists()
        ):
            raise serializers.ValidationError(
                'You are not a journalist at this publisher.'
            )
        return publisher


class NewsletterSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source='author.username', read_only=True
    )
    articles = serializers.PrimaryKeyRelatedField(
        many=True, queryset=approved_articles(), required=False
    )

    class Meta:
        model = Newsletter
        fields = (
            'id',
            'title',
            'description',
            'created_at',
            'author',
            'author_name',
            'articles',
        )
        read_only_fields = ('author', 'created_at')
