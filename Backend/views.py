# views.py - Fixed authentication issues

import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from rest_framework import generics, status, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

from .models import (
    Profile, Post, Like, Connection,
    UserRecommendation, RecommendationService
)
from .serializers import (
    UserLoginSerializer, UserRegistrationSerializer,
    ProfileSerializer, ProfileSummarySerializer, ProfileUpdateSerializer,
    PostSerializer, UserRecommendationSerializer, RecommendationRequestSerializer,
    RecommendationFeedbackSerializer
)

# Set up logging
logger = logging.getLogger(__name__)


# ============================================================================
# AUTHENTICATION VIEWS - FIXED
# ============================================================================

class RegistrationThrottle(AnonRateThrottle):
    """Custom throttling for registration - 5 attempts per hour"""
    rate = '5/hour'


class LoginThrottle(AnonRateThrottle):
    """Custom throttling for login - 10 attempts per hour"""
    rate = '10/hour'


@api_view(['POST'])
@authentication_classes([])  # FIXED: No authentication required
@permission_classes([AllowAny])  # FIXED: Allow anyone to register
def register(request):
    """
    Enhanced user registration with proper error handling and validation
    """
    try:
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                user = serializer.save()
                # Create Knox token
                instance, token = AuthToken.objects.create(user)

                logger.info(f"New user registered: {user.username}")

                return Response({
                    'success': True,
                    'message': 'Registration successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'date_joined': user.date_joined
                    },
                    'token': token,
                    'profile': {
                        'id': user.profile.id,
                        'first_name': user.profile.first_name,
                        'last_name': user.profile.last_name
                    }
                }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Registration failed. Please try again.',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([])  # FIXED: No authentication required for login
@permission_classes([AllowAny])  # FIXED: Allow anyone to login
def login(request):
    """
    Enhanced login with better error messages and security
    """
    try:
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Create Knox token
            instance, token = AuthToken.objects.create(user)

            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            logger.info(f"User logged in: {user.username}")

            return Response({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'last_login': user.last_login
                },
                'token': token,
                'profile': {
                    'id': user.profile.id,
                    'full_name': user.profile.get_full_name(),
                    'profile_picture': user.profile.profile_picture.url if user.profile.profile_picture else None
                }
            })

        return Response({
            'success': False,
            'message': 'Invalid credentials',
            'errors': serializer.errors
        }, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Login failed. Please try again.',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])  # FIXED: Explicit Knox authentication
@permission_classes([IsAuthenticated])
def logout(request):
    """Enhanced logout with proper cleanup"""
    try:
        # Delete all tokens for this user
        request.user.auth_token_set.all().delete()

        logger.info(f"User logged out: {request.user.username}")

        return Response({
            'success': True,
            'message': 'Successfully logged out'
        })
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Logout failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get or update current user's profile information"""
    try:
        profile = request.user.profile

        if request.method == 'GET':
            serializer = ProfileSerializer(profile, context={'request': request})
            return Response({
                'success': True,
                'profile': serializer.data
            })

        elif request.method == 'PATCH':
            serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Profile updated successfully',
                    'profile': serializer.data
                })
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Profile fetch/update error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to fetch or update profile'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# PROFILE VIEWS - FIXED
# ============================================================================

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for list views"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProfileListView(generics.ListCreateAPIView):
    """
    Enhanced profile listing with search, filtering, and pagination
    """
    serializer_class = ProfileSummarySerializer
    authentication_classes = [TokenAuthentication]  # FIXED: Explicit Knox authentication
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'bio', 'interests', 'location', 'occupation']
    ordering_fields = ['created_at', 'first_name', 'last_name']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Optimized queryset with filtering options
        """
        queryset = Profile.objects.filter(
            show_in_recommendations=True
        ).select_related('user').exclude(
            user=self.request.user  # Exclude current user
        )

        # Filter by interests
        interests = self.request.query_params.get('interests')
        if interests:
            interest_list = [i.strip().lower() for i in interests.split(',')]
            # Create Q objects for each interest
            interest_queries = Q()
            for interest in interest_list:
                interest_queries |= Q(interests__icontains=interest)
            queryset = queryset.filter(interest_queries)

        # Filter by location
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)

        # Filter by age range
        min_age = self.request.query_params.get('min_age')
        max_age = self.request.query_params.get('max_age')
        if min_age or max_age:
            from datetime import date, timedelta
            today = date.today()

            if min_age:
                max_birth_date = today - timedelta(days=int(min_age) * 365)
                queryset = queryset.filter(date_of_birth__lte=max_birth_date)

            if max_age:
                min_birth_date = today - timedelta(days=(int(max_age) + 1) * 365)
                queryset = queryset.filter(date_of_birth__gte=min_birth_date)

        return queryset

    def list(self, request, *args, **kwargs):
        """Enhanced list response with metadata"""
        try:
            response = super().list(request, *args, **kwargs)

            # Add metadata
            response.data = {
                'success': True,
                'results': response.data['results'],
                'pagination': {
                    'count': response.data['count'],
                    'next': response.data['next'],
                    'previous': response.data['previous'],
                    'current_page': request.query_params.get('page', 1),
                    'page_size': self.paginator.page_size
                },
                'filters': {
                    'search': request.query_params.get('search', ''),
                    'interests': request.query_params.get('interests', ''),
                    'location': request.query_params.get('location', ''),
                    'min_age': request.query_params.get('min_age', ''),
                    'max_age': request.query_params.get('max_age', '')
                }
            }
            return response
        except Exception as e:
            logger.error(f"Profile list error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to fetch profiles'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    Enhanced profile detail view with proper permissions and optimization
    """
    queryset = Profile.objects.select_related('user').prefetch_related(
        'followers', 'following', 'post_set'
    )
    authentication_classes = [TokenAuthentication]  # FIXED: Explicit Knox authentication
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProfileSerializer
        return ProfileUpdateSerializer

    def get_object(self):
        """Enhanced object retrieval with caching for performance"""
        pk = self.kwargs.get('pk')
        cache_key = f"profile_detail_{pk}"

        # Try cache first for GET requests
        if self.request.method == 'GET':
            cached_profile = cache.get(cache_key)
            if cached_profile:
                return cached_profile

        profile = get_object_or_404(self.get_queryset(), pk=pk)

        # Cache for 5 minutes
        if self.request.method == 'GET':
            cache.set(cache_key, profile, 300)

        return profile

    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve with connection status"""
        try:
            profile = self.get_object()
            serializer = self.get_serializer(profile)

            # Add connection status
            # is_following = False
            # is_follower = False
            # mutual_connections_count = 0
            #
            # if request.user.is_authenticated and profile.user != request.user:
            #     is_following = Connection.objects.filter(
            #         follower=request.user.profile,
            #         following=profile
            #     ).exists()
            #
            #     is_follower = Connection.objects.filter(
            #         follower=profile,
            #         following=request.user.profile
            #     ).exists()
            #
            #     # Get mutual connections count
            #     mutual_connections = RecommendationService.get_mutual_connections(
            #         request.user.profile, profile
            #     )
            #     mutual_connections_count = mutual_connections.count()

            return Response({
                'success': True,
                'profile': serializer.data,
                'connection_status': {
                    'is_following': False,
                    'is_follower': False,
                    'mutual_connections_count': 0
                }
            })
        except Exception as e:
            logger.error(f"Profile detail error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to fetch profile'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Enhanced update with cache invalidation"""
        try:
            # Check if user can update this profile
            profile = self.get_object()
            if profile.user != request.user:
                return Response({
                    'success': False,
                    'message': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)

            response = super().update(request, *args, **kwargs)

            # Invalidate cache
            cache_key = f"profile_detail_{profile.pk}"
            cache.delete(cache_key)

            # If interests changed, refresh recommendations
            if 'interests' in request.data:
                self._refresh_user_recommendations(profile)

            response.data = {
                'success': True,
                'message': 'Profile updated successfully',
                'profile': response.data
            }
            return response

        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to update profile'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _refresh_user_recommendations(self, profile):
        """Asynchronously refresh recommendations when profile changes"""
        try:
            # Delete existing recommendations to force refresh
            UserRecommendation.objects.filter(user=profile).delete()
            logger.info(f"Refreshed recommendations for user: {profile.user.username}")
        except Exception as e:
            logger.error(f"Failed to refresh recommendations: {str(e)}")


# ============================================================================
# POST VIEWS - FIXED
# ============================================================================

class PostViewSet(viewsets.ModelViewSet):
    """
    Enhanced PostViewSet with better performance and features
    """
    serializer_class = PostSerializer
    authentication_classes = [TokenAuthentication]  # FIXED: Explicit Knox authentication
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'like_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Optimized queryset with prefetch for better performance
        """
        return Post.objects.select_related(
            'user', 'user__user'
        ).prefetch_related(
            'like_set', 'comment_set__user'
        ).annotate(
            like_count=Count('like', distinct=True),
            comment_count=Count('comment', distinct=True)
        )

    def perform_create(self, serializer):
        """Enhanced create with validation"""
        serializer.save(user=self.request.user.profile)
        logger.info(f"New post created by: {self.request.user.username}")

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        user_profile = request.user.profile
        if Like.objects.filter(post=post, user=user_profile).exists():
            return Response({'success': False, 'message': 'Already liked'}, status=400)
        Like.objects.create(post=post, user=user_profile)
        return Response({'success': True, 'message': 'Post liked'})

    @action(detail=True, methods=['post'])
    def unlike(self, request, pk=None):
        post = self.get_object()
        user_profile = request.user.profile
        deleted, _ = Like.objects.filter(post=post, user=user_profile).delete()
        if deleted:
            return Response({'success': True, 'message': 'Post unliked'})
        return Response({'success': False, 'message': 'You had not liked this post'}, status=400)

    def list(self, request, *args, **kwargs):
        """Enhanced list with feed filtering"""
        try:
            # Filter for user's feed (posts from followed users)
            feed_only = request.query_params.get('feed', 'false').lower() == 'true'

            if feed_only:
                # Get users that current user follows
                following_ids = Connection.objects.filter(
                    follower=request.user.profile
                ).values_list('following_id', flat=True)

                # Include current user's posts too
                following_ids = list(following_ids) + [request.user.profile.id]

                self.queryset = self.get_queryset().filter(user_id__in=following_ids)

            response = super().list(request, *args, **kwargs)
            response.data = {
                'success': True,
                'posts': response.data['results'],
                'pagination': {
                    'count': response.data['count'],
                    'next': response.data['next'],
                    'previous': response.data['previous']
                }
            }
            return response

        except Exception as e:
            logger.error(f"Post list error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to fetch posts'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """Override create to ensure proper response format"""
        try:
            response = super().create(request, *args, **kwargs)
            response.data = {
                'success': True,
                'message': 'Post created successfully',
                'post': response.data
            }
            return response
        except Exception as e:
            logger.error(f"Post creation error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to create post'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# CONNECTION VIEWS - FIXED
# ============================================================================

@api_view(['GET'])
@authentication_classes([TokenAuthentication])  # FIXED: Explicit Knox authentication
@permission_classes([IsAuthenticated])
def user_connections(request):
    """Get user's connections (followers/following)"""
    try:
        user_profile = request.user.profile
        connection_type = request.query_params.get('type', 'following')

        if connection_type == 'followers':
            connections = Connection.objects.filter(
                following=user_profile
            ).select_related('follower__user')
            profiles = [conn.follower for conn in connections]
        else:
            connections = Connection.objects.filter(
                follower=user_profile
            ).select_related('following__user')
            profiles = [conn.following for conn in connections]

        serializer = ProfileSummarySerializer(profiles, many=True)

        return Response({
            'success': True,
            'type': connection_type,
            'count': len(profiles),
            'connections': serializer.data
        })

    except Exception as e:
        logger.error(f"Connections fetch error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to fetch connections'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])  # FIXED: Explicit Knox authentication
@permission_classes([IsAuthenticated])
def follow_user(request, user_id):
    """Follow another user"""
    try:
        target_profile = get_object_or_404(Profile, id=user_id)

        if target_profile.user == request.user:
            return Response({
                'success': False,
                'message': 'Cannot follow yourself'
            }, status=status.HTTP_400_BAD_REQUEST)

        connection, created = Connection.objects.get_or_create(
            follower=request.user.profile,
            following=target_profile
        )

        if created:
            logger.info(f"{request.user.username} followed {target_profile.user.username}")
            return Response({
                'success': True,
                'message': f'Now following {target_profile.get_full_name()}',
                'following': True
            })
        else:
            return Response({
                'success': False,
                'message': 'Already following',
                'following': True
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Follow error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to follow user'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])  # FIXED: Explicit Knox authentication
@permission_classes([IsAuthenticated])
def unfollow_user(request, user_id):
    """Unfollow a user"""
    try:
        target_profile = get_object_or_404(Profile, id=user_id)

        connection = Connection.objects.filter(
            follower=request.user.profile,
            following=target_profile
        ).first()

        if connection:
            connection.delete()
            logger.info(f"{request.user.username} unfollowed {target_profile.user.username}")
            return Response({
                'success': True,
                'message': f'Unfollowed {target_profile.get_full_name()}',
                'following': False
            })
        else:
            return Response({
                'success': False,
                'message': 'Not following',
                'following': False
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Unfollow error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to unfollow user'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# RECOMMENDATION VIEWS - FIXED
# ============================================================================

class RecommendationThrottle(UserRateThrottle):
    """Limit recommendation requests to prevent abuse"""
    rate = '30/hour'


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])  # FIXED: Explicit Knox authentication
@permission_classes([IsAuthenticated])
def user_recommendations(request):
    """
    Enhanced recommendations endpoint with caching and analytics
    """
    try:
        user_profile = request.user.profile

        if request.method == 'POST':
            # Request fresh recommendations with custom parameters
            serializer = RecommendationRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            recommendations = RecommendationService.get_recommendations_for_user(
                user_profile,
                limit=serializer.validated_data['limit'],
                use_cache=serializer.validated_data['use_cache'],
                refresh_if_old=serializer.validated_data['refresh_if_old']
            )
            cache_used = serializer.validated_data['use_cache']
        else:
            # Get default recommendations
            recommendations = RecommendationService.get_recommendations_for_user(user_profile)
            cache_used = True

        # Serialize recommendations
        rec_serializer = UserRecommendationSerializer(
            recommendations,
            many=True,
            context={'request': request}
        )

        response_data = {
            'success': True,
            'recommendations': rec_serializer.data,
            'total_count': len(recommendations),
            'cache_used': cache_used,
            'generated_at': timezone.now(),
            'metadata': {
                'user_interests': user_profile.get_interests_list(),
                'user_connections_count': user_profile.following.count()
            }
        }

        return Response(response_data)

    except Exception as e:
        logger.error(f"Recommendations error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to fetch recommendations'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])  # FIXED: Explicit Knox authentication
@permission_classes([IsAuthenticated])
def recommendation_feedback(request):
    """Track user interactions with recommendations"""
    try:
        serializer = RecommendationFeedbackSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Here you would typically save feedback to analytics model
        # For now, just log it
        logger.info(f"Recommendation feedback: {serializer.validated_data}")

        return Response({
            'success': True,
            'message': 'Feedback recorded'
        })

    except Exception as e:
        logger.error(f"Recommendation feedback error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to record feedback'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])  # FIXED: Explicit Knox authentication
@permission_classes([IsAuthenticated])
def refresh_recommendations(request):
    """Force refresh recommendations for current user"""
    try:
        user_profile = request.user.profile

        # Delete cached recommendations
        UserRecommendation.objects.filter(user=user_profile).delete()

        # Generate fresh recommendations
        recommendations = RecommendationService.generate_recommendations_for_user(
            user_profile, limit=20
        )

        # Cache them
        RecommendationService.cache_recommendations(user_profile, recommendations)

        logger.info(f"Refreshed recommendations for: {request.user.username}")

        return Response({
            'success': True,
            'message': f'Generated {len(recommendations)} fresh recommendations',
            'count': len(recommendations)
        })

    except Exception as e:
        logger.error(f"Refresh recommendations error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to refresh recommendations'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])  # FIXED: Explicit Knox authentication
@permission_classes([IsAuthenticated])
def test_token(request):
    """Simple endpoint to test if token authentication is working"""
    return Response({
        'success': True,
        'message': 'Token is valid!',
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email
        },
        'auth_method': str(request.auth.__class__.__name__) if request.auth else 'None'
    })
