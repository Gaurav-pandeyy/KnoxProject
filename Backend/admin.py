from django.contrib import admin
from .models import Profile,Post,Comment,Connection
# Register your models here.
admin.site.register(Profile)
admin.site.register(Post)
admin.site.register(Connection)
admin.site.register(Comment)
