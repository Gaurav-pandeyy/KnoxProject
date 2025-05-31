from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Post, Profile, Like, Comment, UserRecommendation, RecommendationService, Connection


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm')

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)

        # Create a blank profile; fields like first_name can be filled later
        Profile.objects.create(user=user)

        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            data['user'] = user
        return data


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'description', 'images', 'created_at', 'author_name', 'like_count', 'is_liked']
        read_only_fields = ['id', 'created_at', 'author_name', 'like_count', 'is_liked']

    def get_author_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    def get_like_count(self, obj):
        return obj.like_set.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(user=request.user.profile, post=obj).exists()
        return False


class PostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['description', 'images']

    def create(self, validated_data):
        # Automatically set the user from request
        request = self.context.get('request')
        validated_data['user'] = request.user.profile
        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'text', 'created_at', 'author_name']
        read_only_fields = ['id', 'created_at', 'author_name']

    def get_author_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user.profile
        return super().create(validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    fullname = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    interests_list = serializers.SerializerMethodField()
    bio_keywords = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'username','fullname', 'first_name', 'last_name', 'bio', 'profile_picture', 'interests', 'interests_list',
                  'location', 'date_of_birth', 'age', 'occupation', 'education', 'bio_keywords',
                  'show_in_recommendations',
                  'followers_count', 'following_count', 'posts_count', 'created_at', 'updated_at'
                  ]
        read_only_fields = [
            'id', 'user', 'fullname', 'age', 'interests_list',
            'bio_keywords', 'followers_count', 'following_count',
            'posts_count', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'date_of_birth': {'write_only': True},  # Keep age private, only show calculated age
        }

    def get_fullname(self, obj):
        return obj.get_full_name()

    def get_age(self, obj):
        return obj.get_age()

    def get_interests_list(self, obj):
        """Get interests as clean list"""
        return obj.get_interests_list()

    def get_bio_keywords(self, obj):
        """Get extracted keywords from bio"""
        return obj.get_bio_keywords()

    def get_followers_count(self, obj):
        """Count of users following this profile"""
        return obj.followers.count()

    def get_following_count(self, obj):
        """Count of users this profile follows"""
        return obj.following.count()

    def get_posts_count(self, obj):
        """Count of posts by this user"""
        return obj.post_set.count()

    def validate_interests(self, value):
        """
        Validate interests format and content

        Rules:
        - Maximum 10 interests
        - Each interest max 50 characters
        - No empty interests after splitting
        """
        if not value:
            return value

        interests_list = [interest.strip() for interest in value.split(',')]
        interests_list = [interest for interest in interests_list if interest]  # Remove empty

        if len(interests_list) > 10:
            raise serializers.ValidationError("Maximum 10 interests allowed")

        for interest in interests_list:
            if len(interest) > 50:
                raise serializers.ValidationError(f"Interest '{interest}' is too long (max 50 characters)")
            if len(interest) < 2:
                raise serializers.ValidationError(f"Interest '{interest}' is too short (min 2 characters)")

        # Return cleaned interests as comma-separated string
        return ', '.join(interests_list)


class ProfileSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight profile serializer for listings and recommendations

    Contains only essential information for displaying in lists
    """
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    interests_list = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'bio',
            'profile_picture', 'interests_list', 'location', 'age', 'occupation'
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_age(self, obj):
        return obj.get_age()

    def get_interests_list(self, obj):
        return obj.get_interests_list()


class MutualConnectionSerializer(serializers.ModelSerializer):
    """Serializer for displaying mutual connections in recommendations"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'first_name', 'last_name', 'full_name', 'profile_picture']

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserRecommendationSerializer(serializers.ModelSerializer):
    """
    Serializer for cached user recommendations

    Includes:
    - Recommended user's profile summary
    - Recommendation score and metrics
    - Human-readable reason
    - Mutual connections (optional, for detailed view)
    """
    recommended_user = ProfileSummarySerializer(read_only=True)
    mutual_connections = serializers.SerializerMethodField()
    score_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserRecommendation
        fields = [
            'id', 'recommended_user', 'score', 'score_percentage',
            'mutual_connections_count', 'common_interests_count',
            'reason', 'mutual_connections', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_score_percentage(self, obj):
        """Convert score to percentage for display"""
        return round(obj.score * 100, 1)

    def get_mutual_connections(self, obj):
        """
        Get mutual connections (only in detailed view to avoid N+1 queries)

        Only included if 'include_mutual_connections' is in context
        """
        request = self.context.get('request')
        if not request or not request.query_params.get('include_mutual_connections'):
            return None

        mutual_connections = RecommendationService.get_mutual_connections(
            obj.user, obj.recommended_user
        )
        return MutualConnectionSerializer(mutual_connections, many=True).data


class RecommendationRequestSerializer(serializers.Serializer):
    """
    Serializer for recommendation request parameters

    Used to validate parameters when requesting fresh recommendations
    """
    limit = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=50,
        help_text="Number of recommendations to return (1-50)"
    )
    min_score = serializers.FloatField(
        default=0.1,
        min_value=0.0,
        max_value=1.0,
        help_text="Minimum recommendation score (0.0-1.0)"
    )
    use_cache = serializers.BooleanField(
        default=True,
        help_text="Whether to use cached recommendations"
    )
    refresh_if_old = serializers.BooleanField(
        default=True,
        help_text="Whether to refresh old cached recommendations"
    )
    include_mutual_connections = serializers.BooleanField(
        default=False,
        help_text="Whether to include mutual connections details"
    )


class RecommendationResponseSerializer(serializers.Serializer):
    """
    Serializer for recommendation API responses

    Wraps recommendations with metadata
    """
    recommendations = UserRecommendationSerializer(many=True)
    total_count = serializers.IntegerField()
    cache_used = serializers.BooleanField()
    generated_at = serializers.DateTimeField()

    class Meta:
        fields = ['recommendations', 'total_count', 'cache_used', 'generated_at']


class RecommendationStatsSerializer(serializers.Serializer):
    """
    Serializer for recommendation statistics and insights

    Provides analytics about recommendation system performance
    """
    total_recommendations = serializers.IntegerField()
    avg_score = serializers.FloatField()
    score_distribution = serializers.DictField()
    top_reasons = serializers.ListField(child=serializers.DictField())
    mutual_connections_stats = serializers.DictField()
    interests_stats = serializers.DictField()

    class Meta:
        fields = [
            'total_recommendations', 'avg_score', 'score_distribution',
            'top_reasons', 'mutual_connections_stats', 'interests_stats'
        ]


class ConnectionSerializer(serializers.ModelSerializer):
    """Serializer for user connections (following/followers)"""
    follower = ProfileSummarySerializer(read_only=True)
    following = ProfileSummarySerializer(read_only=True)

    class Meta:
        model = Connection
        fields = ['id', 'follower', 'following', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating profile information

    Allows partial updates and validates changes
    """

    class Meta:
        model = Profile
        fields = [
            'first_name', 'last_name', 'bio', 'profile_picture',
            'interests', 'location', 'date_of_birth', 'occupation',
            'education', 'show_in_recommendations'
        ]

    def validate(self, data):
        """Custom validation for profile updates"""
        # Ensure first_name and last_name are provided together or not at all
        if 'first_name' in data and 'last_name' not in data:
            if not self.instance.last_name:
                raise serializers.ValidationError({
                    'last_name': 'Last name is required when setting first name'
                })

        if 'last_name' in data and 'first_name' not in data:
            if not self.instance.first_name:
                raise serializers.ValidationError({
                    'first_name': 'First name is required when setting last name'
                })

        return data

    def validate_interests(self, value):
        """Reuse interests validation from ProfileSerializer"""
        serializer = ProfileSerializer()
        return serializer.validate_interests(value)


class RecommendationFeedbackSerializer(serializers.Serializer):
    """
    Serializer for recommendation feedback

    Allows users to provide feedback on recommendations
    """
    recommendation_id = serializers.IntegerField()
    action = serializers.ChoiceField(
        choices=[
            ('viewed', 'Viewed'),
            ('profile_clicked', 'Profile Clicked'),
            ('connected', 'Connected'),
            ('dismissed', 'Dismissed'),
            ('reported', 'Reported')
        ]
    )
    feedback_text = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional feedback text"
    )

    def validate_recommendation_id(self, value):
        """Validate that recommendation exists and belongs to current user"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")

        try:
            recommendation = UserRecommendation.objects.get(
                id=value,
                user__user=request.user
            )
        except UserRecommendation.DoesNotExist:
            raise serializers.ValidationError("Recommendation not found")

        return value
class ProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            'first_name', 'last_name', 'bio', 'interests',
            'location', 'date_of_birth', 'occupation', 'education',
            'show_in_recommendations'
        ]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
