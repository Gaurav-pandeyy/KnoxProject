# models.py - Enhanced models with detailed explanations

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
import re


class Profile(models.Model):
    """Extended user profile with recommendation-relevant fields"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    bio = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(upload_to="profile_pics/user_%Y_%m_%d/", blank=True)

    # NEW FIELDS FOR RECOMMENDATIONS
    interests = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated interests (e.g., 'photography, travel, cooking')"
    )
    location = models.CharField(max_length=100, blank=True)

    # METADATA FOR BETTER RECOMMENDATIONS
    date_of_birth = models.DateField(null=True, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    education = models.CharField(max_length=200, blank=True)

    # PRIVACY SETTINGS
    show_in_recommendations = models.BooleanField(
        default=True,
        help_text="Allow others to see you in their recommendations"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_interests_list(self):
        """
        Convert comma-separated interests string to clean list

        Example: "Photography, Travel,cooking" → ["photography", "travel", "cooking"]

        Steps:
        1. Split by comma: ["Photography", " Travel", "cooking"]  
        2. Strip whitespace: ["Photography", "Travel", "cooking"]
        3. Convert to lowercase: ["photography", "travel", "cooking"]
        4. Remove empty entries: filters out cases like "photography,, travel"

        Why lowercase? For consistent matching - "Photography" should match "photography"
        """
        if not self.interests:
            return []

        interests_list = []
        for interest in self.interests.split(','):
            cleaned_interest = interest.strip().lower()
            if cleaned_interest:  # Only add non-empty strings
                interests_list.append(cleaned_interest)

        return interests_list

    def get_bio_keywords(self):
        """
        Extract meaningful keywords from user bio for interest matching

        Example bio: "I am a photographer who loves travel and food"
        Result: ["photographer", "loves", "travel", "food"]

        Process:
        1. Convert to lowercase for consistent matching
        2. Use regex to find all words (letters/numbers only)
        3. Filter out common words (I, am, the, etc.) - these don't indicate interests
        4. Filter out short words (less than 3 characters) - usually not meaningful
        """
        if not self.bio:
            return []

        # Common words that don't indicate interests or personality
        common_words = {
            'i', 'am', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'love', 'like', 'enjoy', 'who', 'what', 'where', 'when', 'why', 'how'
        }

        # Extract all words using regex (only letters and numbers)
        words = re.findall(r'\b\w+\b', self.bio.lower())

        # Filter out common words and short words
        meaningful_words = []
        for word in words:
            if len(word) > 2 and word not in common_words:
                meaningful_words.append(word)

        return meaningful_words

    def get_full_name(self):
        """Helper method for display purposes"""
        return f"{self.first_name} {self.last_name}".strip()

    def get_age(self):
        """Calculate age from date of birth"""
        if not self.date_of_birth:
            return None

        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class Post(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    images = models.ImageField(upload_to="post_images/post_%Y_%m_%d/")
    description = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post by {self.user.first_name}"


class Comment(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.first_name} on {self.post}"


class Like(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')  # Prevents duplicate likes

    def __str__(self):
        return f"{self.user.first_name} likes {self.post}"


class Connection(models.Model):
    follower = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')  # Prevents duplicate connections

    def __str__(self):
        return f"{self.follower.first_name} follows {self.following.first_name}"


class UserRecommendation(models.Model):
    """
    Stores pre-calculated user recommendations for performance

    Why we need this model:
    - Calculating recommendations in real-time is expensive (lots of database queries)
    - We pre-calculate and cache recommendations
    - Can be updated periodically (daily/weekly) or when user data changes
    """
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='recommendations',
        help_text="User who will see this recommendation"
    )
    recommended_user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='recommended_to',
        help_text="User being recommended"
    )

    # RECOMMENDATION METRICS
    score = models.FloatField(
        default=0.0,
        help_text="Overall recommendation score (0.0 to 1.0)"
    )
    mutual_connections_count = models.IntegerField(
        default=0,
        help_text="Number of mutual connections"
    )
    common_interests_count = models.IntegerField(
        default=0,
        help_text="Number of common interests"
    )

    # HUMAN-READABLE EXPLANATION
    reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Why this user was recommended (e.g., '3 mutual connections, 2 common interests')"
    )

    # METADATA
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'recommended_user')  # One recommendation per user pair
        ordering = ['-score', '-created_at']  # Best recommendations first

    def __str__(self):
        return f"Recommend {self.recommended_user.first_name} to {self.user.first_name} (Score: {self.score:.2f})"


class RecommendationService:
    """
    Service class containing all recommendation logic

    This is a utility class (no database model) that contains methods for:
    - Finding mutual connections
    - Calculating interest similarity  
    - Computing recommendation scores
    - Generating and caching recommendations
    """

    @staticmethod
    def get_mutual_connections(user_profile, target_profile):
        """
        Find mutual connections between two users

        Logic:
        1. Get all users that user_profile follows
        2. Get all users that target_profile follows  
        3. Find intersection (users both follow)

        Example:
        - User A follows: [John, Mary, Bob, Sarah]
        - User B follows: [Mary, Bob, Tom, Lisa]  
        - Mutual connections: [Mary, Bob]
        """
        # Get IDs of users that user_profile follows
        user_following_ids = set(
            Connection.objects.filter(follower=user_profile).values_list('following_id', flat=True)
        )

        # Get IDs of users that target_profile follows
        target_following_ids = set(
            Connection.objects.filter(follower=target_profile).values_list('following_id', flat=True)
        )

        # Find common user IDs (intersection of sets is faster than database joins)
        mutual_following_ids = user_following_ids.intersection(target_following_ids)

        # Return actual Profile objects for the mutual connections
        return Profile.objects.filter(id__in=mutual_following_ids)

    @staticmethod
    def calculate_interest_similarity(user_profile, target_profile):
        """
        Calculate how similar two users are based on interests and bio

        Uses Jaccard Similarity: similarity = |A ∩ B| / |A ∪ B|

        Steps:
        1. Get interests for both users
        2. Get bio keywords for both users
        3. Combine interests + keywords for each user
        4. Calculate intersection (common) and union (total unique)
        5. Return count of common interests and similarity ratio

        Example:
        User A: interests=["photography", "travel"] + bio_keywords=["photographer", "adventure"]
        User B: interests=["travel", "cooking"] + bio_keywords=["chef", "adventure", "food"]

        Combined:
        User A: {"photography", "travel", "photographer", "adventure"}
        User B: {"travel", "cooking", "chef", "adventure", "food"}

        Common: {"travel", "adventure"} = 2 items
        Total unique: {"photography", "travel", "photographer", "adventure", "cooking", "chef", "food"} = 7 items
        Similarity = 2/7 = 0.286
        """
        # Get interests as sets for fast intersection/union operations
        user_interests = set(user_profile.get_interests_list())
        target_interests = set(target_profile.get_interests_list())

        # Get bio keywords as sets
        user_bio_keywords = set(user_profile.get_bio_keywords())
        target_bio_keywords = set(target_profile.get_bio_keywords())

        # Combine interests and bio keywords for each user
        user_all_interests = user_interests.union(user_bio_keywords)
        target_all_interests = target_interests.union(target_bio_keywords)

        # Handle edge case: if either user has no interests/keywords
        if not user_all_interests or not target_all_interests:
            return 0, 0.0

        # Find common interests (intersection)
        common_interests = user_all_interests.intersection(target_all_interests)

        # Calculate Jaccard similarity coefficient
        union_interests = user_all_interests.union(target_all_interests)
        similarity_score = len(common_interests) / len(union_interests) if union_interests else 0.0

        return len(common_interests), similarity_score

    @staticmethod
    def calculate_activity_similarity(user_profile, target_profile):
        """
        Calculate similarity based on user activity patterns

        Logic: Users who like/comment on the same posts might have similar interests

        Steps:
        1. Get all posts user_profile has liked or commented on
        2. Get all posts target_profile has liked or commented on
        3. Count how many posts both users have interacted with

        This helps find users with similar content preferences even if they
        don't explicitly list the same interests
        """
        # Get post IDs that user_profile has interacted with
        user_interactions = set()

        # Add posts the user has liked
        user_liked_posts = Like.objects.filter(user=user_profile).values_list('post_id', flat=True)
        user_interactions.update(user_liked_posts)

        # Add posts the user has commented on
        user_commented_posts = Comment.objects.filter(user=user_profile).values_list('post_id', flat=True)
        user_interactions.update(user_commented_posts)

        # Get post IDs that target_profile has interacted with
        target_interactions = set()

        # Add posts the target has liked
        target_liked_posts = Like.objects.filter(user=target_profile).values_list('post_id', flat=True)
        target_interactions.update(target_liked_posts)

        # Add posts the target has commented on
        target_commented_posts = Comment.objects.filter(user=target_profile).values_list('post_id', flat=True)
        target_interactions.update(target_commented_posts)

        # Handle edge case: if either user has no interactions
        if not user_interactions or not target_interactions:
            return 0

        # Count common interactions (posts both users have interacted with)
        common_interactions = user_interactions.intersection(target_interactions)
        return len(common_interactions)

    @staticmethod
    def calculate_recommendation_score(user_profile, target_profile):
        """
        Calculate overall recommendation score using weighted combination of factors

        Scoring factors:
        1. Mutual connections (40% weight) - "Friends of friends"
        2. Interest similarity (40% weight) - Similar hobbies/interests  
        3. Activity similarity (20% weight) - Similar content preferences

        Each factor is normalized to 0-1 range, then combined with weights
        Final score is between 0.0 (no similarity) and 1.0 (perfect match)
        """
        # Get mutual connections count
        mutual_connections = RecommendationService.get_mutual_connections(user_profile, target_profile)
        mutual_count = mutual_connections.count()

        # Get interest similarity
        common_interests_count, interest_similarity = RecommendationService.calculate_interest_similarity(
            user_profile, target_profile
        )

        # Get activity similarity
        activity_similarity = RecommendationService.calculate_activity_similarity(user_profile, target_profile)

        # Define weights (should sum to 1.0)
        mutual_weight = 0.4  # 40% importance to mutual connections
        interest_weight = 0.4  # 40% importance to interests
        activity_weight = 0.2  # 20% importance to activity patterns

        # Normalize scores to 0-1 range
        # Cap mutual connections at 5 (more than 5 mutual = 100% score)
        mutual_score = min(mutual_count / 5.0, 1.0)

        # interest_similarity is already 0-1 (Jaccard coefficient)

        # Cap activity similarity at 10 interactions (more than 10 = 100% score)  
        activity_score = min(activity_similarity / 10.0, 1.0)

        # Calculate weighted final score
        total_score = (
                mutual_score * mutual_weight +
                interest_similarity * interest_weight +
                activity_score * activity_weight
        )

        return {
            'total_score': total_score,
            'mutual_connections_count': mutual_count,
            'common_interests_count': common_interests_count,
            'activity_similarity': activity_similarity,
            'mutual_connections': mutual_connections  # For displaying who the mutual connections are
        }

    @staticmethod
    def generate_recommendation_reason(score_data):
        """
        Generate human-readable explanation for why user was recommended

        Examples:
        - "Based on 3 mutual connections"
        - "Based on 2 common interests"  
        - "Based on 1 mutual connection, 3 common interests"
        - "Based on similar activity patterns"
        """
        reasons = []

        if score_data['mutual_connections_count'] > 0:
            count = score_data['mutual_connections_count']
            reasons.append(f"{count} mutual connection{'s' if count != 1 else ''}")

        if score_data['common_interests_count'] > 0:
            count = score_data['common_interests_count']
            reasons.append(f"{count} common interest{'s' if count != 1 else ''}")

        if score_data['activity_similarity'] > 0:
            reasons.append("similar activity patterns")

        if not reasons:
            return "Based on your network"

        return "Based on " + ", ".join(reasons)

    @classmethod
    def generate_recommendations_for_user(cls, user_profile, limit=10, min_score=0.1):
        """
        Generate fresh recommendations for a user

        Process:
        1. Get all users except current connections and self
        2. Calculate recommendation score for each candidate
        3. Filter by minimum score threshold  
        4. Sort by score (best first)
        5. Return top N recommendations

        Args:
            user_profile: Profile to generate recommendations for
            limit: Maximum number of recommendations to return
            min_score: Minimum score threshold (0.0 to 1.0)
        """
        # Get users this person is already connected to (exclude from recommendations)
        current_connections = set(
            Connection.objects.filter(follower=user_profile).values_list('following_id', flat=True)
        )
        # Also exclude self
        current_connections.add(user_profile.id)

        # Get potential candidates (users not already connected to)
        # Also exclude users who opted out of recommendations
        candidates = Profile.objects.exclude(
            id__in=current_connections
        ).filter(
            show_in_recommendations=True
        )

        recommendations = []

        # Calculate recommendation score for each candidate
        for candidate in candidates:
            score_data = cls.calculate_recommendation_score(user_profile, candidate)

            # Only include if score meets minimum threshold
            if score_data['total_score'] >= min_score:
                reason = cls.generate_recommendation_reason(score_data)

                recommendation = {
                    'user': user_profile,
                    'recommended_user': candidate,
                    'score': score_data['total_score'],
                    'mutual_connections_count': score_data['mutual_connections_count'],
                    'common_interests_count': score_data['common_interests_count'],
                    'reason': reason,
                    'mutual_connections': score_data['mutual_connections']
                }
                recommendations.append(recommendation)

        # Sort by score (highest first)
        recommendations.sort(key=lambda x: x['score'], reverse=True)

        return recommendations[:limit]

    @classmethod
    def cache_recommendations(cls, user_profile, recommendations):
        """
        Save recommendations to database for faster future access

        This replaces any existing cached recommendations for this user
        """
        # Delete existing cached recommendations
        UserRecommendation.objects.filter(user=user_profile).delete()

        # Create new recommendation records
        recommendation_objects = []
        for rec_data in recommendations:
            recommendation_objects.append(
                UserRecommendation(
                    user=rec_data['user'],
                    recommended_user=rec_data['recommended_user'],
                    score=rec_data['score'],
                    mutual_connections_count=rec_data['mutual_connections_count'],
                    common_interests_count=rec_data['common_interests_count'],
                    reason=rec_data['reason']
                )
            )

        # Bulk create for better performance
        UserRecommendation.objects.bulk_create(recommendation_objects)

    @classmethod
    def get_recommendations_for_user(cls, user_profile, limit=10, use_cache=True, refresh_if_old=True):
        """
        Get recommendations for a user (from cache or generate fresh)

        Args:
            user_profile: Profile to get recommendations for
            limit: Number of recommendations to return
            use_cache: Whether to use cached recommendations
            refresh_if_old: Whether to refresh if cached recommendations are old
        """
        if use_cache:
            # Try to get cached recommendations
            cached_recommendations = UserRecommendation.objects.filter(
                user=user_profile
            ).select_related('recommended_user')[:limit]

            if cached_recommendations.exists():
                # Check if cache is too old (optional)
                if refresh_if_old:
                    from django.utils import timezone
                    from datetime import timedelta

                    latest_rec = cached_recommendations.first()
                    if (timezone.now() - latest_rec.updated_at) > timedelta(days=7):
                        # Cache is older than 7 days, refresh
                        return cls._refresh_recommendations(user_profile, limit)

                return list(cached_recommendations)

        # Generate fresh recommendations
        return cls._refresh_recommendations(user_profile, limit)

    @classmethod
    def _refresh_recommendations(cls, user_profile, limit=10):
        """Generate and cache fresh recommendations"""
        recommendations = cls.generate_recommendations_for_user(user_profile, limit=limit)
        cls.cache_recommendations(user_profile, recommendations)

        # Return as UserRecommendation objects for consistency
        return UserRecommendation.objects.filter(user=user_profile)[:limit]